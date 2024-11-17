import React from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';


const LogInPage = () => {
    const navigate = useNavigate()
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleLogIn = (e) => {
        e.preventDefault();
        if (!username || !password) {
            alert('Please enter both username and password.');
            return;
          }
        navigate('/profilesetup'); // Redirect to ProfileSetUp
      };

  return (
    <div className="flex flex-col justify-center items-center h-screen bg-gray-100">
      <h1 className="text-4xl font-bold mb-12 text-blue-600 font-playfair">WHAT 2 EAT</h1>
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold text-center mb-6">Welcome</h2>
        <form onSubmit={handleLogIn} action="/login" method="POST" className="space-y-4">
          <div>
            <input
              type="text"
              name="username"
              placeholder="Username"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <input
              type="password"
              name="password"
              placeholder="Password"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Log In
          </button>
          <a class="inline-block align-baseline font-bold text-sm text-blue-500 hover:text-blue-800" href="#">
            Forgot Password?
         </a>
        </form>
        <div className="text-center mt-4 text-gray-600">
          Don't have an account?{' '}
          <Link to="/signup" className="text-blue-500 hover:underline">
          Sign Up</Link>
        </div>
      </div>
    </div>
  )
}

export default LogInPage
