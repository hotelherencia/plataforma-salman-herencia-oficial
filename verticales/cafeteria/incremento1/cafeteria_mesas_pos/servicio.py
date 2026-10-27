import itertools
import threading
from dataclasses import replace
from datetime import datetime, timedelta

from .dominio import (
    Alerta,
    Comanda,
    EntradaLedger,
    EstadoGasto,
    EstadoMesa,
    EstadoPedido,
    EstadoPropuesta,
    GastoBorrador,
    Insumo,
    ItemPedido,
    Mesa,
    MovimientoInsumo,
    PagoItem,
    Parte,
    Producto,
    PropuestaCompra,
    Reparto,
)
from .empresa import EMPRESA_FIJA, Empresa
from .puertos import PuertosVacios

EMPRESA_DESCONOCIDA = "empresa desconocida"
QR_INVALIDO = "qr invalido o revocado"
ITEM_ENVIADO = "item ya enviado a cocina: requiere flujo autorizado"
ITEM_YA_PAGADO = "item ya pagado"
VENTA_DUPLICADA = "venta ya imputada"
PARTE_YA_PAGADA = "parte ya pagada"
ROL_APROBADOR = "administrador"
HORAS_EXPIRACION_PROPUESTA = 48


class AccesoDenegado(Exception):
    pass


class FlujoAutorizadoRequerido(Exception):
    pass


class ServicioCafeteria:
    def __init__(
        self,
        empresa: Empresa = EMPRESA_FIJA,
        puertos: PuertosVacios | None = None,
    ) -> None:
        self._empresa = empresa
        self._puertos = puertos if puertos is not None else PuertosVacios()
        self._mesas: dict[str, Mesa] = {}
        self._productos: dict[str, Producto] = {}
        self._insumos: dict[str, Insumo] = {}
        self._items: list[ItemPedido] = []
        self._comandas: dict[str, Comanda] = {}
        self._pagos: list[PagoItem] = []
        self._reparto: Reparto | None = None
        self._movimientos: list[MovimientoInsumo] = []
        self._ventas_imputadas: set[str] = set()
        self._gastos: dict[str, GastoBorrador] = {}
        self._propuestas: dict[str, PropuestaCompra] = {}
        self._alertas: dict[str, Alerta] = {}
        self._ledger: list[EntradaLedger] = []
        self._ids = itertools.count(1)
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def abrir_mesa(self, empresa_id: str, mesa_id: str) -> Mesa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = Mesa(id=mesa_id, qr_token=self._nuevo_id("QR"), estado=EstadoMesa.ACTIVA)
            self._mesas[mesa_id] = mesa
            return mesa

    def revocar_qr(self, empresa_id: str, mesa_id: str) -> Mesa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = self._mesas[mesa_id]
            revocada = replace(mesa, estado=EstadoMesa.REVOCADA)
            self._mesas[mesa_id] = revocada
            return revocada

    def _mesa_por_token(self, token: str) -> Mesa:
        for mesa in self._mesas.values():
            if mesa.qr_token == token:
                return mesa
        raise AccesoDenegado(QR_INVALIDO)

    def acceder_carta(self, empresa_id: str, token: str) -> Mesa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = self._mesa_por_token(token)
            if mesa.estado is not EstadoMesa.ACTIVA:
                self._ledger.append(self._entrada("acceso_carta", "qr revocado", "cliente", "denegado"))
                raise AccesoDenegado(QR_INVALIDO)
            return mesa

    def cargar_carta(self, empresa_id: str, productos: tuple[Producto, ...], insumos: tuple[Insumo, ...]) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._productos = {p.id: p for p in productos}
            self._insumos = {i.id: i for i in insumos}

    def agregar_item(self, empresa_id: str, token: str, producto_id: str, cantidad: int, cliente: str) -> ItemPedido:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = self._mesa_por_token(token)
            if mesa.estado is not EstadoMesa.ACTIVA:
                raise AccesoDenegado(QR_INVALIDO)
            producto = self._productos[producto_id]
            item = ItemPedido(
                producto_id=producto_id,
                cantidad=cantidad,
                cliente=cliente,
                precio_clp=producto.precio_clp,
            )
            self._items.append(item)
            return item

    def confirmar_pedido(self, empresa_id: str, token: str, clave: str, ahora: datetime) -> Comanda:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            existente = next((c for c in self._comandas.values() if c.pedido_id == clave), None)
            if existente is not None:
                return existente
            mesa = self._mesa_por_token(token)
            pendientes = [
                replace(it, enviado=True)
                for it in self._items
                if not it.enviado
            ]
            if not pendientes:
                raise ValueError("no hay ítems pendientes")
            self._items = pendientes + [it for it in self._items if it.enviado]
            comanda = Comanda(
                id=self._nuevo_id("CMD"),
                pedido_id=clave,
                mesa_id=mesa.id,
                hora=ahora,
                estado=EstadoPedido.ENVIADO.value,
            )
            self._comandas[clave] = comanda
            self._ledger.append(self._entrada("confirmar_pedido", "una sola comanda por clave", "cliente", "ok", ahora))
            return comanda

    def editar_item_enviado(self, empresa_id: str, token: str, producto_id: str) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._mesa_por_token(token)
            if any(it.producto_id == producto_id and it.enviado for it in self._items):
                self._ledger.append(self._entrada("editar_item", "ítem enviado", "cliente", "denegado"))
                raise FlujoAutorizadoRequerido(ITEM_ENVIADO)
            raise ValueError("no hay ítem enviado con ese producto")

    def total_mesa(self, empresa_id: str, token: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._mesa_por_token(token)
            return sum(it.precio_clp * it.cantidad for it in self._items)

    def pagar_items(self, empresa_id: str, token: str, cliente: str, clave_item: str, monto_clp: int) -> PagoItem:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = self._mesa_por_token(token)
            if any(p.item_clave == clave_item and p.cliente == cliente for p in self._pagos):
                raise ValueError(ITEM_YA_PAGADO)
            if any(p.item_clave == clave_item for p in self._pagos):
                raise ValueError(ITEM_YA_PAGADO)
            pago = PagoItem(
                id=self._nuevo_id("PAG"),
                mesa_id=mesa.id,
                item_clave=clave_item,
                cliente=cliente,
                monto_clp=monto_clp,
            )
            self._pagos.append(pago)
            return pago

    def reparto_igual(self, empresa_id: str, token: str, partes: int, descuento_clp: int = 0, propina_clp: int = 0) -> Reparto:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            mesa = self._mesa_por_token(token)
            total = (
                sum(it.precio_clp * it.cantidad for it in self._items)
                - descuento_clp
                + propina_clp
            )
            base, residuo = divmod(total, partes)
            nuevas = []
            for i in range(partes):
                anterior = next(
                    (p for p in (self._reparto.partes if self._reparto else ()) if p.cliente == f"parte-{i+1}"),
                    None,
                )
                if anterior and anterior.pagada:
                    nuevas.append(anterior)
                    continue
                monto = base + residuo if i == partes - 1 else base
                nuevas.append(Parte(cliente=f"parte-{i+1}", monto_clp=monto))
            reparto = Reparto(
                mesa_id=mesa.id,
                partes=tuple(nuevas),
                descuento_clp=descuento_clp,
                propina_clp=propina_clp,
            )
            self._reparto = reparto
            return reparto

    def pagar_parte(self, empresa_id: str, token: str, cliente: str, clave: str, monto_clp: int) -> Parte:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._mesa_por_token(token)
            if self._reparto is None:
                raise ValueError("no hay reparto")
            if any(p.clave_pago == clave and p.pagada for p in self._reparto.partes):
                raise ValueError(PARTE_YA_PAGADA)
            partes = []
            for parte in self._reparto.partes:
                if parte.cliente == cliente:
                    if parte.pagada:
                        raise ValueError(PARTE_YA_PAGADA)
                    if parte.monto_clp != monto_clp:
                        raise ValueError("el monto no coincide con la parte")
                    partes.append(
                        replace(parte, pagada=True, clave_pago=clave)
                    )
                else:
                    partes.append(parte)
            self._reparto = replace(self._reparto, partes=tuple(partes))
            return self._reparto.partes[[p.cliente for p in self._reparto.partes].index(cliente)]

    def vender(self, empresa_id: str, producto_id: str, cantidad: int, clave_venta: str) -> list[MovimientoInsumo]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if clave_venta in self._ventas_imputadas:
                return [m for m in self._movimientos if m.venta_id == clave_venta]
            producto = self._productos[producto_id]
            self._ventas_imputadas.add(clave_venta)
            if not producto.tiene_receta:
                return []
            movimientos = []
            for insumo_id, por_unidad in producto.receta:
                insumo = self._insumos[insumo_id]
                consumo = por_unidad * cantidad
                self._insumos[insumo_id] = replace(insumo, stock=insumo.stock - consumo)
                movimiento = MovimientoInsumo(
                    insumo_id=insumo_id, cantidad=consumo, venta_id=clave_venta
                )
                self._movimientos.append(movimiento)
                movimientos.append(movimiento)
            return movimientos

    def margen_producto(self, empresa_id: str, producto_id: str) -> tuple[str, float | None]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            producto = self._productos[producto_id]
            if not producto.tiene_receta:
                return ("no_calculable", None)
            costo = 0.0
            for insumo_id, por_unidad in producto.receta:
                insumo = self._insumos[insumo_id]
                if insumo.costo_clp is None:
                    return ("no_calculable", None)
                costo += insumo.costo_clp * por_unidad
            if costo == 0:
                return ("no_calculable", None)
            margen = (producto.precio_clp - costo) / producto.precio_clp
            return ("calculable", margen)

    def registrar_gasto_borrador(
        self, empresa_id: str, proveedor: str, monto_clp: int, fecha: str, lineas_erroneas: int
    ) -> GastoBorrador:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            gasto = GastoBorrador(
                id=self._nuevo_id("GST"),
                proveedor=proveedor,
                monto_clp=monto_clp,
                fecha=fecha,
                estado=EstadoGasto.PENDIENTE,
                lineas_erroneas=lineas_erroneas,
            )
            self._gastos[gasto.id] = gasto
            self._ledger.append(self._entrada("gasto", "borrador pendiente de aprobación", "ocr", "pendiente"))
            return gasto

    def aprobar_gasto(self, empresa_id: str, gasto_id: str, rol: str, correcciones: tuple[str, ...]) -> GastoBorrador:
        self._exigir_empresa(empresa_id)
        if rol != ROL_APROBADOR:
            raise AccesoDenegado("rol no autorizado")
        with self._cerrojo:
            gasto = self._gastos[gasto_id]
            aprobado = replace(
                gasto, estado=EstadoGasto.APROBADO, correcciones=correcciones
            )
            self._gastos[gasto_id] = aprobado
            self._ledger.append(self._entrada("gasto", "aprobación con corrección del OCR", rol, "aprobado"))
            return aprobado

    def generar_propuestas_compra(self, empresa_id: str, ahora: datetime) -> list[PropuestaCompra]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            propuestas = []
            for insumo in self._insumos.values():
                if insumo.stock < insumo.stock_minimo:
                    cantidad = (insumo.stock_minimo - insumo.stock) * 2
                    costo = int(cantidad * (insumo.costo_clp or 0))
                    propuesta = PropuestaCompra(
                        id=self._nuevo_id("PPC"),
                        insumo_id=insumo.id,
                        cantidad=cantidad,
                        costo_clp=costo,
                        creada_en=ahora,
                        expira_en=ahora + timedelta(hours=HORAS_EXPIRACION_PROPUESTA),
                        estado=EstadoPropuesta.PENDIENTE,
                    )
                    self._propuestas[propuesta.id] = propuesta
                    propuestas.append(propuesta)
            return propuestas

    def usar_propuesta(self, empresa_id: str, propuesta_id: str, ahora: datetime, rol: str) -> PropuestaCompra:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            propuesta = self._propuestas[propuesta_id]
            if ahora > propuesta.expira_en:
                expirada = replace(propuesta, estado=EstadoPropuesta.EXPIRADA)
                self._propuestas[propuesta_id] = expirada
                self._ledger.append(self._entrada("propuesta", "datos vencidos: exige revisión", "sistema", "bloqueado", ahora))
                raise ValueError("propuesta expirada: exige revisión")
            if rol != ROL_APROBADOR:
                raise AccesoDenegado("sin aprobación humana no se ejecuta la compra")
            ejecutada = replace(propuesta, estado=EstadoPropuesta.EJECUTADA)
            self._propuestas[propuesta_id] = ejecutada
            self._ledger.append(self._entrada("propuesta", "compra ejecutada bajo aprobación", rol, "ejecutada", ahora))
            return ejecutada

    def alerta_anulacion(
        self, empresa_id: str, hecho_id: str, monto_clp: int, umbral_clp: int, ahora: datetime
    ) -> Alerta | None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if monto_clp <= umbral_clp:
                return None
            existente = next((a for a in self._alertas.values() if a.hecho_id == hecho_id), None)
            if existente is not None:
                return existente
            alerta = Alerta(
                id=self._nuevo_id("ALT"),
                hecho_id=hecho_id,
                umbral_clp=umbral_clp,
                monto_clp=monto_clp,
                creada_en=ahora,
            )
            self._alertas[alerta.id] = alerta
            self._ledger.append(
                self._entrada("anulacion", f"umbral {umbral_clp} registrado; sin sanción automática", "sistema", "alerta", ahora)
            )
            return alerta

    def ledger(self, empresa_id: str) -> tuple[EntradaLedger, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(self._ledger)

    def _entrada(self, fuente: str, regla: str, actor: str, resultado: str, cuando: datetime | None = None) -> EntradaLedger:
        return EntradaLedger(
            fuente=fuente,
            regla=regla,
            actor=actor,
            resultado=resultado,
            cuando=cuando or datetime.now(),
        )

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _nuevo_id(self, prefijo: str) -> str:
        return f"{prefijo}-SINT-{next(self._ids):04d}"


def cafeteria_sintetica() -> ServicioCafeteria:
    servicio = ServicioCafeteria()
    servicio.cargar_carta(
        empresa_id=servicio.empresa.id,
        productos=(
            Producto(
                id="PROD-CAFE",
                nombre="Café americano",
                precio_clp=2_500,
                receta=(("INS-CAFE", 1.0), ("INS-LECHE", 0.5)),
                version=1,
            ),
            Producto(
                id="PROD-SIN-RECETA",
                nombre="Producto sin receta",
                precio_clp=1_000,
                receta=(),
                tiene_receta=False,
            ),
        ),
        insumos=(
            Insumo(id="INS-CAFE", nombre="Café molido", stock=10.0, costo_clp=800.0, stock_minimo=2.0),
            Insumo(id="INS-LECHE", nombre="Leche", stock=5.0, costo_clp=400.0, stock_minimo=1.0),
            Insumo(id="INS-SIN-COSTO", nombre="Insumo sin costo", stock=3.0, costo_clp=None, stock_minimo=1.0),
        ),
    )
    return servicio
