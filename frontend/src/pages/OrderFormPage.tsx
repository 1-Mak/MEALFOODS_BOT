import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getDeliveryPoints } from "../api/counterparties";
import { getProducts } from "../api/products";
import { createOrder, updateOrder, cancelOrder, getOrder } from "../api/orders";
import type { DeliveryPoint, Product, Order } from "../types";

const FULL_EDIT_STAGES = new Set(["Заказано"]);
const QTY_EDIT_STAGES = new Set(["Зарезервировано"]);

interface CartItem {
  product: Product;
  quantity: number;
}

function formatPrice(n: number) {
  return n.toLocaleString("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
}

function calcSummary(items: CartItem[]) {
  let totalPrice = 0;
  let netWeight = 0;
  let grossWeight = 0;
  let boxes = 0;

  for (const { product, quantity } of items) {
    totalPrice += product.price * quantity;
    netWeight += product.net_weight * quantity;
    grossWeight += product.gross_weight * quantity;
    boxes += Math.ceil(quantity / product.box_multiplicity);
  }

  return { totalPrice, netWeight, grossWeight, boxes };
}

export default function OrderFormPage() {
  const navigate = useNavigate();
  const { orderId } = useParams<{ orderId?: string }>();
  const [params] = useSearchParams();
  const cpGuid = params.get("cp") || "";
  const cpName = params.get("cpName") || "";

  const isNew = !orderId;

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const defaultDate = tomorrow.toISOString().split("T")[0];

  const [tab, setTab] = useState<"main" | "products">("main");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [deliveryDate, setDeliveryDate] = useState(defaultDate);
  const [deliveryPoints, setDeliveryPoints] = useState<DeliveryPoint[]>([]);
  const [selectedDp, setSelectedDp] = useState("");

  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState("");

  const [existingOrder, setExistingOrder] = useState<Order | null>(null);

  const isFullEdit = isNew || (existingOrder ? FULL_EDIT_STAGES.has(existingOrder.stage) : false);
  const isQtyEdit = existingOrder ? QTY_EDIT_STAGES.has(existingOrder.stage) : false;
  const canEdit = isNew || isFullEdit || isQtyEdit;

  useEffect(() => {
    const load = async () => {
      try {
        const [points, prods] = await Promise.all([
          getDeliveryPoints(cpGuid),
          getProducts(cpGuid),
        ]);
        setDeliveryPoints(points);
        setProducts(prods);

        if (points.length === 1) setSelectedDp(points[0].e4_guid);

        if (!isNew && orderId) {
          const order = await getOrder(orderId!);
          setExistingOrder(order);
          setDeliveryDate(order.delivery_date);
          setSelectedDp(order.delivery_point_guid);

          const cartItems: CartItem[] = order.items
            .map((item) => {
              const product = prods.find((p) => p.e4_guid === item.product_guid);
              if (!product) return null;
              return { product, quantity: item.quantity };
            })
            .filter(Boolean) as CartItem[];
          setCart(cartItems);
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [cpGuid, orderId, isNew]);

  function setQty(productGuid: string, qty: number) {
    if (qty <= 0) {
      setCart((prev) => prev.filter((c) => c.product.e4_guid !== productGuid));
    } else {
      setCart((prev) => {
        const existing = prev.find((c) => c.product.e4_guid === productGuid);
        if (existing) {
          return prev.map((c) =>
            c.product.e4_guid === productGuid ? { ...c, quantity: qty } : c,
          );
        }
        const product = products.find((p) => p.e4_guid === productGuid)!;
        return [...prev, { product, quantity: qty }];
      });
    }
  }

  function getQty(productGuid: string) {
    return cart.find((c) => c.product.e4_guid === productGuid)?.quantity || 0;
  }

  async function handleConfirm() {
    if (!selectedDp || cart.length === 0) return;
    setSaving(true);
    try {
      if (isNew) {
        await createOrder({
          counterparty_guid: cpGuid,
          delivery_point_guid: selectedDp,
          delivery_date: deliveryDate,
          items: cart.map((c) => ({ product_guid: c.product.e4_guid, quantity: c.quantity })),
        });
      } else {
        const body: any = {
          items: cart.map((c) => ({ product_guid: c.product.e4_guid, quantity: c.quantity })),
        };
        if (isFullEdit) {
          body.delivery_point_guid = selectedDp;
          body.delivery_date = deliveryDate;
        }
        await updateOrder(orderId!, body);
      }
      navigate(-1);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleCancel() {
    if (!orderId) return;
    if (!confirm("Отменить заказ?")) return;
    setSaving(true);
    try {
      await cancelOrder(orderId!);
      navigate(-1);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  const summary = calcSummary(cart);
  const canConfirm = !saving && selectedDp !== "" && cart.length > 0;
  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  );

  if (loading) return <div className="loading-screen"><p>Загрузка...</p></div>;
  if (error) return <div className="error-screen"><p>{error}</p></div>;

  return (
    <div className="page">
      <header className="page-header">
        <button className="back-btn" onClick={() => navigate(-1)}>‹</button>
        <h1>{isNew ? "Новый заказ" : "Заказ"}</h1>
      </header>

      <div className="tabs">
        <button className={`tab ${tab === "main" ? "active" : ""}`} onClick={() => setTab("main")}>
          Основное
        </button>
        <button className={`tab ${tab === "products" ? "active" : ""}`} onClick={() => setTab("products")}>
          Товары {cart.length > 0 && `(${cart.length})`}
        </button>
      </div>

      <div className="page-content">
        {tab === "main" && (
          <>
            <div className="field">
              <label>Дата доставки</label>
              <input
                type="date"
                value={deliveryDate}
                disabled={!isFullEdit && !isNew}
                onChange={(e) => setDeliveryDate(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Адрес доставки</label>
              <select
                value={selectedDp}
                disabled={!isFullEdit && !isNew}
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

            {existingOrder && (
              <div className="field">
                <label>Статус</label>
                <div style={{ padding: "11px 12px", background: "white", borderRadius: "10px", border: "1px solid #ddd", fontSize: 15, color: "#333" }}>
                  {existingOrder.status}
                </div>
              </div>
            )}

            {existingOrder && canEdit && (
              <button className="cancel-order-btn" onClick={handleCancel} disabled={saving}>
                Отменить заказ
              </button>
            )}
          </>
        )}

        {tab === "products" && (
          <>
            <input
              className="search-input"
              type="text"
              placeholder="Поиск товара..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {products.length === 0 ? (
              <div className="empty-state">Матрица товаров пуста</div>
            ) : filteredProducts.length === 0 ? (
              <div className="empty-state">Ничего не найдено</div>
            ) : (
              filteredProducts.map((product) => {
                const qty = getQty(product.e4_guid);
                return (
                  <div key={product.e4_guid} className={`product-row ${qty > 0 ? "product-row--active" : ""}`}>
                    <div className="product-row-top">
                      <div className="product-row-name">{product.name}</div>
                      <div className="product-row-unit-price">{formatPrice(product.price)} / {product.unit}</div>
                    </div>

                    {qty === 0 ? (
                      <div className="product-row-collapsed">
                        <span className="product-row-hint">Кратность: {product.box_multiplicity} {product.unit}</span>
                        {canEdit && (
                          <button className="add-btn" onClick={() => setQty(product.e4_guid, 1)}>
                            + Добавить
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="product-row-expanded">
                        <span className="product-row-hint">Кратность: {product.box_multiplicity} {product.unit}</span>
                        <div className="product-row-controls">
                          <button className="qty-btn" onClick={() => setQty(product.e4_guid, qty - 1)}>−</button>
                          <span className="qty-value">{qty}</span>
                          <button className="qty-btn" disabled={!canEdit} onClick={() => setQty(product.e4_guid, qty + 1)}>+</button>
                          <span className="product-row-price">{formatPrice(product.price * qty)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </>
        )}
      </div>

      <div className="order-bottom">
        {cart.length > 0 && (
          <div className="order-summary">
            <div className="order-summary-row">
              <span>Вес нетто</span>
              <span>{summary.netWeight.toFixed(2)} кг</span>
            </div>
            <div className="order-summary-row">
              <span>Вес брутто</span>
              <span>{summary.grossWeight.toFixed(2)} кг</span>
            </div>
            <div className="order-summary-row">
              <span>Коробов</span>
              <span>{summary.boxes}</span>
            </div>
            <div className="order-summary-row total">
              <span>Итого</span>
              <span>{formatPrice(summary.totalPrice)}</span>
            </div>
          </div>
        )}

        {canEdit && (
          <div className="confirm-bar">
            <button className="confirm-bar-btn" disabled={!canConfirm} onClick={handleConfirm}>
              {saving ? "Сохраняем..." : "Подтвердить заказ"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
