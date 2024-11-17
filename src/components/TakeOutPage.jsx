// import React, { useState, useEffect } from 'react';
// import axios from 'axios';

// const TakeOutPage = () => {
//   const [restaurants, setRestaurants] = useState('');
//   const [isLoading, setIsLoading] = useState(true);

//   useEffect(() => {
//     const fetchTakeOutPlaces = async () => {
//       try {
//         const response = await axios.post(
//           'http://localhost:5001/takeout',
//           {},
//           {
//             withCredentials: true, // Include credentials
//           }
//         );
//         setRestaurants(response.data.restaurants || '');
//       } catch (error) {
//         console.error('Error fetching take-out places:', error);
//         alert('Failed to fetch take-out places. Please try again.');
//       } finally {
//         setIsLoading(false);
//       }
//     };

//     fetchTakeOutPlaces();
//   }, []);

//   return (
//     <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
//       <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
//         <h2 className="text-2xl font-bold mb-4">Nearby restaurants</h2>
//         {isLoading ? (
//           <p>Loading...</p>
//         ) : (
//           <p>{restaurants}</p>
//         )}
//       </div>
//     </div>
//   );
// };

// export default TakeOutPage;

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TakeOutPage = () => {
  const [restaurants, setRestaurants] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTakeOutPlaces = async () => {
      try {
        const response = await axios.post(
          'http://localhost:5001/takeout',
          {},
          {
            withCredentials: true, // Include credentials
          }
        );
        // Assuming the response contains a list of restaurant details as a string,
        // split the string into an array if needed
        const restaurantList = response.data.restaurants.split('\n').filter(item => item.trim() !== '');
        setRestaurants(restaurantList);
      } catch (error) {
        console.error('Error fetching take-out places:', error);
        alert('Failed to fetch take-out places. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTakeOutPlaces();
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <div className="w-full max-w-3xl bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4">Nearby Restaurants</h2>
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <ul className="list-disc list-inside">
            {restaurants.map((restaurant, index) => (
              <li key={index} className="text-gray-700">
                {restaurant}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default TakeOutPage;

