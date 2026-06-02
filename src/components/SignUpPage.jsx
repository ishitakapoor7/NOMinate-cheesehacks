import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const SignUpPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSignUp = async (e) => {
    e.preventDefault();

    if (!formData.username || !formData.email || !formData.password || !formData.confirmPassword) {
      alert('Please fill in all fields.');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match!');
      return;
    }

    try {
      const response = await axios.post(
        'http://localhost:5001/signup',
        {
          username: formData.username,
          email: formData.email,
          password: formData.password,
        },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true,
        }
      );

      if (response.status === 201) {
        navigate('/profilesetup');
      }
    } catch (error) {
      if (error.response && error.response.status === 409) {
        alert('User already exists. Please use a different email.');
      } else {
        alert('An error occurred. Please try again later.');
      }
      console.error(error.response?.data || error.message);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-orange-50 via-amber-50 to-rose-50 p-4">
      <div className="text-center mb-8 animate-fade-in-up">
        <h1 className="text-5xl font-playfair font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">
          NOMinate
        </h1>
        <p className="text-gray-500 mt-2 font-semibold">Let's find your perfect meal 🍳</p>
      </div>

      <div className="bg-white/80 backdrop-blur p-8 rounded-3xl shadow-xl w-full max-w-md animate-fade-in-up">
        <h2 className="text-2xl font-extrabold text-center mb-6 text-gray-800">Create an account</h2>
        <form onSubmit={handleSignUp} className="space-y-4">
          <input
            type="text"
            name="username"
            placeholder="Username"
            value={formData.username}
            onChange={handleChange}
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
          />
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={formData.email}
            onChange={handleChange}
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={formData.password}
            onChange={handleChange}
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
          />
          <input
            type="password"
            name="confirmPassword"
            placeholder="Confirm Password"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            className="w-full px-4 h-12 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-orange-400 transition-colors"
          />
          <button
            type="submit"
            className="w-full h-12 bg-gradient-to-r from-orange-500 to-rose-500 text-white font-bold rounded-xl hover:opacity-90 shadow-md transition-all"
          >
            Sign Up
          </button>
        </form>
        <div className="text-center mt-6 text-gray-600 font-semibold">
          Already have an account?{' '}
          <Link to="/" className="text-orange-500 hover:underline">
            Log In
          </Link>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
