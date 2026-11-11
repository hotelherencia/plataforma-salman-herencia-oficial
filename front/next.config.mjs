/** La única variable del front es API_BASE_URL (origen del servicio).
 *  Contención prod: vacío → /api (rewrite same-origin a Railway). */
export default {
  env: {
    API_BASE_URL: process.env.API_BASE_URL || "/api",
  },
};
