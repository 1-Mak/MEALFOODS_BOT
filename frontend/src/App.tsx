import { BrowserRouter, Routes, Route } from "react-router-dom";
import { MaxUI } from "@maxhub/max-ui";
import "@maxhub/max-ui/dist/styles.css";
import HomePage from "./pages/HomePage";
import "./App.css";

function App() {
  return (
    <MaxUI>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          {/* Этап 4-6: catalog, cart, orders */}
        </Routes>
      </BrowserRouter>
    </MaxUI>
  );
}

export default App;
