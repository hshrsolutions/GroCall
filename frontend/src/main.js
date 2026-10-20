import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { applyBrand } from "./store"
import "./main.css"

applyBrand()
createApp(App).use(router).mount("#app")
