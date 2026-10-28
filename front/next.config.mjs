/** La única variable del front es API_BASE_URL (origen del servicio). */
export default {
  env: {
    API_BASE_URL: process.env.API_BASE_URL ?? "",
  },
};
