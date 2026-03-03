import { BrowserRouter, Routes, Route } from "react-router-dom";
import { MaxUI } from "@maxhub/max-ui";
import "@maxhub/max-ui/dist/styles.css";
import HomePage from "./pages/HomePage";
import OrdersPage from "./pages/OrdersPage";
import OrderFormPage from "./pages/OrderFormPage";
import "./App.css";

function App() {
  return (
    <MaxUI>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/new" element={<OrderFormPage />} />
          <Route path="/orders/:orderId" element={<OrderFormPage />} />
        </Routes>
      </BrowserRouter>
    </MaxUI>
  );
}

export default App;
