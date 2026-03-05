import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { authenticate } from "../api/auth";
import type { AuthResponse, Counterparty } from "../types";
import ErrorDetails from "../components/ErrorDetails";

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [selectedCp, setSelectedCp] = useState<Counterparty | null>(null);

  useEffect(() => {
    authenticate()
      .then((data) => {
        setAuth(data);
        if (data.counterparties.length === 1) {
          setSelectedCp(data.counterparties[0]);
        }
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

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
        <p>{error.message || String(error)}</p>
        <ErrorDetails error={error} />
      </div>
    );
  }

  const counterparties = auth?.counterparties || [];

  return (
    <div className="page">
      <header className="page-header">
        <h1>Личный кабинет</h1>
      </header>

      <div className="page-content">
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

        <div className="nav-buttons">
          <Button
            mode="primary"
            size="large"
            stretched
            disabled={!selectedCp}
            onClick={() => navigate(`/orders?cp=${selectedCp!.e4_guid}&cpName=${encodeURIComponent(selectedCp!.name)}`)}
          >
            Список заказов
          </Button>
        </div>
      </div>

      <footer className="page-footer">
        ООО «Милфудс» 2026г.
      </footer>
    </div>
  );
}
