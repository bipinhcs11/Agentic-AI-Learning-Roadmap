import React from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, ShoppingCart, Truck } from "lucide-react";
import "./styles.css";

const samplePayload = {
  schema: "a2ui.grocery.catalog.v1",
  component: "GroceryCatalogGrid",
  props: {
    title: "Fresh grocery picks",
    query: "breakfast",
    items: [
      {
        sku: "produce-berries",
        name: "Organic strawberries",
        category: "Produce",
        price: 4.99,
        image_url:
          "https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=600&q=80",
        tags: ["fruit", "snack", "breakfast"],
      },
      {
        sku: "dairy-yogurt",
        name: "Greek yogurt",
        category: "Dairy",
        price: 5.49,
        image_url:
          "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=600&q=80",
        tags: ["protein", "breakfast", "smoothie"],
      },
      {
        sku: "bakery-sourdough",
        name: "Sourdough loaf",
        category: "Bakery",
        price: 6.25,
        image_url: "https://source.unsplash.com/600x400/?sourdough,bread",
        tags: ["bread", "sandwich", "artisan"],
      },
    ],
  },
};

function GroceryCatalogGrid({ payload }) {
  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <p className="eyebrow">A2UI payload renderer</p>
          <h1>{payload.props.title}</h1>
        </div>
        <div className="status-strip" aria-label="security controls">
          <span>
            <ShieldCheck size={16} /> JIT scoped
          </span>
          <span>
            <Truck size={16} /> A2A delivery
          </span>
          <span>
            <ShoppingCart size={16} /> UCP checkout
          </span>
        </div>
      </section>

      <section className="catalog-grid" aria-label="grocery items">
        {payload.props.items.map((item) => (
          <article className="product-card" key={item.sku}>
            <img src={item.image_url} alt={item.name} />
            <div className="product-body">
              <div>
                <p className="category">{item.category}</p>
                <h2>{item.name}</h2>
              </div>
              <p className="price">${item.price.toFixed(2)}</p>
              <div className="tags">
                {item.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <button type="button">Add to cart</button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GroceryCatalogGrid payload={samplePayload} />
  </React.StrictMode>,
);
