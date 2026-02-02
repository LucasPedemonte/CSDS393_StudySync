import React from 'react';

const HomePage = () => {
  return (
    <div style={containerStyle}>
      {/* Navigation Bar */}
      <nav style={navStyle}>
        <div style={logoStyle}>StudySync</div>
        <div>
          <button style={textButtonStyle}>Sign In</button>
          <button style={signUpButtonStyle}>Sign Up</button>
        </div>
      </nav>

      {/* Hero Section */}
      <header style={heroSection}>
        <h1 style={mainTitle}>Learn together,<br />grow faster.</h1>
        <p style={subTitle}>
          A single workspace to sync notes, share materials, and collaborate 
          with your study group — all in real time.
        </p>
        
        <div style={featureBar}>
          <span>Shared Notebooks</span> • 
          <span>Live Collaboration</span> • 
          <span>Material Sharing</span> • 
          <span>Study Groups</span>
        </div>
      </header>

      {/* Registration Form Area */}
      <section style={formSection}>
        <div style={card}>
          <h2 style={{ marginBottom: '20px' }}>Create Account</h2>
          
          <input type="text" placeholder="Full Name" style={inputStyle} />
          <input type="email" placeholder="Email" style={inputStyle} />
          <input type="password" placeholder="Password" style={inputStyle} />
          
          <button style={primaryButtonStyle}>Create Account</button>
          
          <div style={divider}>or</div>
          
          <button style={googleButtonStyle}>
            Continue with Google
          </button>
          
          <p style={footerText}>
            Already have an account? <span style={{ color: '#0984e3', cursor: 'pointer' }}>Sign in</span>
          </p>
        </div>
      </section>

      <footer style={{ padding: '20px', fontSize: '0.8rem', color: '#636e72' }}>
        Developed by Team #5: Ana Gómez, Ohta Kamiya, Sheila Monera Cabarique, & Lucas Pedemonte
      </footer>
    </div>
  );
};

// --- STYLES ---
const containerStyle = {
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  backgroundColor: '#f0f2f5',
  minHeight: '100vh',
  color: '#2d3436'
};

const navStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '20px 50px',
  backgroundColor: 'white',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
};

const logoStyle = {
  fontSize: '1.5rem',
  fontWeight: 'bold',
  color: '#0984e3'
};

const heroSection = {
  textAlign: 'center',
  padding: '60px 20px',
  background: 'linear-gradient(135deg, #0984e3 0%, #6c5ce7 100%)',
  color: 'white'
};

const mainTitle = {
  fontSize: '3rem',
  lineHeight: '1.2',
  marginBottom: '20px'
};

const subTitle = {
  fontSize: '1.2rem',
  maxWidth: '600px',
  margin: '0 auto 30px auto',
  opacity: '0.9'
};

const featureBar = {
  fontWeight: 'bold',
  wordSpacing: '10px'
};

const formSection = {
  display: 'flex',
  justifyContent: 'center',
  marginTop: '-50px', // Pulls form up into the hero section slightly
  paddingBottom: '50px'
};

const card = {
  backgroundColor: 'white',
  padding: '40px',
  borderRadius: '12px',
  boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
  width: '100%',
  maxWidth: '400px',
  textAlign: 'center'
};

const inputStyle = {
  width: '100%',
  padding: '12px',
  margin: '10px 0',
  borderRadius: '6px',
  border: '1px solid #dfe6e9',
  boxSizing: 'border-box'
};

const primaryButtonStyle = {
  width: '100%',
  padding: '14px',
  backgroundColor: '#0984e3',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  fontWeight: 'bold',
  marginTop: '10px',
  cursor: 'pointer'
};

const googleButtonStyle = {
  width: '100%',
  padding: '12px',
  backgroundColor: 'white',
  color: '#2d3436',
  border: '1px solid #dfe6e9',
  borderRadius: '6px',
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center'
};

const textButtonStyle = {
  background: 'none',
  border: 'none',
  color: '#2d3436',
  marginRight: '20px',
  cursor: 'pointer'
};

const signUpButtonStyle = {
  padding: '10px 20px',
  backgroundColor: '#0984e3',
  color: 'white',
  border: 'none',
  borderRadius: '5px',
  cursor: 'pointer'
};

const divider = {
  margin: '20px 0',
  color: '#b2bec3',
  fontSize: '0.9rem'
};

const footerText = {
  marginTop: '20px',
  fontSize: '0.9rem',
  color: '#636e72'
};

export default HomePage;