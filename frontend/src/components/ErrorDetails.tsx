import { useState } from "react";

export default function ErrorDetails({ error }: { error: any }) {
  const [open, setOpen] = useState(false);

  const details = {
    status: error?.status,
    url: error?.url,
    message: error?.message,
    body: error?.body,
  };

  return (
    <div style={{ marginTop: 16, width: "100%" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: "none",
          border: "1px solid #ccc",
          borderRadius: 8,
          padding: "8px 16px",
          color: "#666",
          cursor: "pointer",
          fontSize: 13,
        }}
      >
        {open ? "Скрыть подробности" : "Подробнее"}
      </button>
      {open && (
        <pre
          style={{
            marginTop: 12,
            padding: 12,
            background: "#f5f5f5",
            borderRadius: 8,
            fontSize: 12,
            textAlign: "left",
            overflowX: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            color: "#333",
          }}
        >
          {JSON.stringify(details, null, 2)}
        </pre>
      )}
    </div>
  );
}
