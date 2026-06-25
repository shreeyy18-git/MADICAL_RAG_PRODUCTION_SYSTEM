import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signIn, signUp, signInWithGoogle } from "../services/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) {
        await signUp(email, password);
        navigate("/dashboard");
        return;
      }
      await signIn(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed");
    }
    setLoading(false);
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <span className="logo-icon">+</span>
          <h2>Medical AI</h2>
          <p>{isRegister ? "Create your account" : "Sign in to continue"}</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 6 characters"
              required
              minLength={6}
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? "Loading..." : isRegister ? "Register" : "Login"}
          </button>
        </form>

        <div className="divider"><span>or</span></div>

        <button onClick={handleGoogle} className="btn btn-outline btn-full">
          Login with Google
        </button>

        <p className="switch-mode">
          {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
          <button className="link-btn" onClick={() => setIsRegister(!isRegister)}>
            {isRegister ? "Login" : "Register"}
          </button>
        </p>

        <Link to="/" className="back-link">&larr; Back to Home</Link>
      </div>
    </div>
  );
}
