export default function Card({ title, value, icon }) {
  return (
    <div className="card">
      <div className="card-icon">{icon}</div>
      <div className="card-body">
        <h3>{value}</h3>
        <p>{title}</p>
      </div>
    </div>
  );
}
