import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <section className="hero">
        <h1>Medical AI Assistant</h1>
        <p className="hero-sub">
          Understand diseases, symptoms, prevention, treatment, and medical
          concepts with AI-powered retrieval from trusted medical knowledge.
        </p>
        <Link to="/login" className="btn btn-primary btn-lg">Get Started</Link>
      </section>

      <section className="features">
        <div className="feature-card">
          <div className="feature-icon">D</div>
          <h3>Diseases</h3>
          <p>Detailed disease information from medical encyclopedias</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">P</div>
          <h3>Prevention</h3>
          <p>Learn prevention measures for various conditions</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">T</div>
          <h3>Treatments</h3>
          <p>Treatment knowledge grounded in trusted sources</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">E</div>
          <h3>Medical Edu</h3>
          <p>Support for medical students and professionals</p>
        </div>
      </section>

      <section className="how-it-works">
        <h2>How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-num">1</div>
            <h4>Upload Knowledge</h4>
            <p>Admin ingests trusted medical PDFs once</p>
          </div>
          <div className="step-arrow">&rarr;</div>
          <div className="step">
            <div className="step-num">2</div>
            <h4>AI Retrieval</h4>
            <p>System searches relevant medical information</p>
          </div>
          <div className="step-arrow">&rarr;</div>
          <div className="step">
            <div className="step-num">3</div>
            <h4>Accurate Answers</h4>
            <p>Get cited answers with source references</p>
          </div>
        </div>
      </section>

      <footer className="footer">
        <p>Medical AI Assistant &copy; 2026. Not a substitute for professional medical advice.</p>
      </footer>
    </div>
  );
}
