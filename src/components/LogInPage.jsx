import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const LogInPage = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogIn = async (e) => {
    e.preventDefault();

    if (!username || !password) {
      alert('Please enter both username and password.');
      return;
    }

    try {
      const response = await axios.post(
        'http://localhost:5001/login',
        { email: username, password: password },
        { withCredentials: true }
      );

      if (response.status === 200) {
        navigate('/profilesetup');
      }
    } catch (error) {
      console.error('Login error:', error);
      if (error.response && error.response.status === 401) {
        alert('Invalid credentials. Please try again.');
      } else {
        alert('An error occurred. Please try again later.');
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="text-center mb-8 animate-fade-in-up">
        <h1 className="text-5xl font-playfair font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">
          NOMinate
        </h1>
        <p className="text-gray-500 mt-2 font-semibold">Your next favorite meal, picked for you 🍽️</p>
      </div>

      <div className="bg-white/80 backdrop-blur p-8 rounded-3xl shadow-xl w-full max-w-md animate-fade-in-up">
        <h2 className="text-2xl font-extrabold text-center mb-6 text-gray-800">Welcome back</h2>
        <form onSubmit={handleLogIn} className="space-y-4">
          <input
            type="text"
            name="username"
            placeholder="Email"
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="submit"
            className="w-full h-12 bg-gradient-to-r from-orange-500 to-rose-500 text-white font-bold rounded-xl hover:opacity-90 shadow-md transition-all"
          >
            Log In
          </button>
        </form>
        <div className="text-center mt-6 text-gray-600 font-semibold">
          Don't have an account?{' '}
          <Link to="/signup" className="text-orange-500 hover:underline">
            Sign Up
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LogInPage;
