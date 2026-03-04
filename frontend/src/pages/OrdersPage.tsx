import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { getOrders } from "../api/orders";
import type { Order } from "../types";

const EDITABLE_STAGES = new Set(["Заказано", "Зарезервировано"]);

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("ru-RU");
}

function formatPrice(price: number) {
  return price.toLocaleString("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
}

function getCardClass(order: Order) {
  if (order.status === "Отменён") return "order-card cancelled";
  if (EDITABLE_STAGES.has(order.stage)) return "order-card editable";
  return "order-card";
}

export default function OrdersPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const cpGuid = params.get("cp") || "";
  const cpName = params.get("cpName") || "";

  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cpGuid) return;
    getOrders(cpGuid)
      .then(setOrders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [cpGuid]);

  if (loading) return <div className="loading-screen"><p>Загрузка...</p></div>;
  if (error) return <div className="error-screen"><p>{error}</p></div>;

  return (
    <div className="page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>Список заказов</h1>
      </header>

      <div className="page-content">
        {cpName && (
          <div className="cp-card">
            <p className="cp-label">Контрагент</p>
            <h2 className="cp-name">{cpName}</h2>
          </div>
        )}

        <div className="nav-buttons">
          <Button
            mode="primary"
            size="large"
            stretched
            onClick={() => navigate(`/orders/new?cp=${cpGuid}&cpName=${encodeURIComponent(cpName)}`)}
          >
            Создать заказ
          </Button>
        </div>

        {orders.length === 0 ? (
          <div className="empty-state">Заказов пока нет</div>
        ) : (
          <div className="orders-list">
            {orders.map((order) => (
              <div
                key={order.e4_guid}
                className={getCardClass(order)}
                onClick={() => navigate(`/orders/${order.e4_guid}?cp=${cpGuid}&cpName=${encodeURIComponent(cpName)}`)}
              >
                <div className="order-card-row">
                  <span className="order-date">Доставка: {formatDate(order.delivery_date)}</span>
                  <span className="order-price">{formatPrice(order.total_price)}</span>
                </div>
                <div className="order-card-row">
                  <span className="order-status">{order.status}</span>
                  {EDITABLE_STAGES.has(order.stage) && order.status !== "Отменён" && (
                    <span className="order-edit-badge">Доступен к редактированию</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="page-footer">ООО «Милфудс» 2026г.</footer>
    </div>
  );
}
