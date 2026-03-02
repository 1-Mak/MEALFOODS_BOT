import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { authenticate } from "../api/auth";
import { getDeliveryPoints } from "../api/counterparties";
import type { AuthResponse, Counterparty, DeliveryPoint } from "../types";

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [selectedCp, setSelectedCp] = useState<Counterparty | null>(null);
  const [deliveryPoints, setDeliveryPoints] = useState<DeliveryPoint[]>([]);
  const [selectedDp, setSelectedDp] = useState<string>("");
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const defaultDate = tomorrow.toISOString().split("T")[0];
  const [deliveryDate, setDeliveryDate] = useState<string>(defaultDate);

  // Auth on mount
  useEffect(() => {
    authenticate()
      .then((data) => {
        setAuth(data);
        if (data.counterparties.length === 1) {
          setSelectedCp(data.counterparties[0]);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Load delivery points when counterparty changes
  useEffect(() => {
    if (!selectedCp) {
      setDeliveryPoints([]);
      setSelectedDp("");
      return;
    }
    getDeliveryPoints(selectedCp.e4_guid)
      .then((points) => {
        setDeliveryPoints(points);
        if (points.length === 1) {
          setSelectedDp(points[0].e4_guid);
        }
      })
      .catch(() => setDeliveryPoints([]));
  }, [selectedCp]);

  if (loading) {
    return (
      <div className="loading-screen">
        <p>Загрузка...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <p>{error}</p>
      </div>
    );
  }

  const counterparties = auth?.counterparties || [];

  return (
    <div className="page">
      <header className="page-header">
        <h1>Главная</h1>
      </header>

      <div className="page-content">
        {/* Counterparty card */}
        <div className="cp-card">
          <p className="cp-label">Контрагент</p>
          <h2 className="cp-name">
            {counterparties.length === 1
              ? counterparties[0].name
              : selectedCp?.name || "Не выбран"}
          </h2>
        </div>

        {counterparties.length > 1 && (
          <div className="field">
            <label>Сменить контрагента</label>
            <select
              value={selectedCp?.e4_guid || ""}
              onChange={(e) => {
                const cp = counterparties.find(
                  (c) => c.e4_guid === e.target.value,
                );
                setSelectedCp(cp || null);
              }}
            >
              <option value="">-- Выберите --</option>
              {counterparties.map((cp) => (
                <option key={cp.e4_guid} value={cp.e4_guid}>
                  {cp.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Delivery date */}
        <div className="field">
          <label>Дата доставки</label>
          <input
            type="date"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
          />
        </div>

        {/* Delivery address */}
        {selectedCp && (
          <div className="field">
            <label>Адрес доставки</label>
            <select
              value={selectedDp}
              onChange={(e) => setSelectedDp(e.target.value)}
            >
              <option value="">-- Выберите --</option>
              {deliveryPoints.map((dp) => (
                <option key={dp.e4_guid} value={dp.e4_guid}>
                  {dp.address}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="nav-buttons">
          <Button
            mode="primary"
            size="large"
            stretched
            disabled={!selectedCp}
            onClick={() => navigate("/catalog")}
          >
            Каталог товаров
          </Button>

          <Button
            mode="primary"
            size="large"
            stretched
            onClick={() => navigate("/cart")}
          >
            Моя корзина
          </Button>

          <Button
            mode="secondary"
            size="large"
            stretched
            onClick={() => navigate("/orders")}
          >
            Мои заказы
          </Button>
        </div>
      </div>

      <footer className="page-footer">
        ООО «Милфудс» 2026г.
      </footer>
    </div>
  );
}
