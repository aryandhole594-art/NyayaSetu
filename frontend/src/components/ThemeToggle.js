import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

export const lightTheme = {
  '--bg-color': '#f8f9fa',
  '--bg-light': '#ffffff',
  '--bg-dark': '#212529',
  '--bg-dark-lighter': '#343a40',
  '--text-color': '#212529',
  '--text-color-secondary': '#6c757d',
  '--border-color': '#dee2e6',
  '--border-color-dark': '#495057',
  '--primary-color': '#4070f4',
  '--primary-color-dark': '#2952c8',
  '--secondary-color': '#6c757d',
  '--success-color': '#28a745',
  '--danger-color': '#dc3545',
  '--warning-color': '#ffc107',
  '--info-color': '#17a2b8',
  '--shadow-color': 'rgba(0, 0, 0, 0.1)',
};

export const darkTheme = {
  '--bg-color': '#212529',
  '--bg-light': '#343a40',
  '--bg-dark': '#121416',
  '--bg-dark-lighter': '#2c3237',
  '--text-color': '#f8f9fa',
  '--text-color-secondary': '#adb5bd',
  '--border-color': '#495057',
  '--border-color-dark': '#6c757d',
  '--primary-color': '#4070f4',
  '--primary-color-dark': '#2952c8',
  '--secondary-color': '#adb5bd',
  '--success-color': '#28a745',
  '--danger-color': '#dc3545',
  '--warning-color': '#ffc107',
  '--info-color': '#17a2b8',
  '--shadow-color': 'rgba(0, 0, 0, 0.3)',
};

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button 
      className={`theme-toggle ${isDark ? 'dark' : 'light'}`}
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <div className="toggle-track">
        <div className={`toggle-icon sun ${isDark ? 'fade-out' : 'fade-in'}`}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2"/>
            <path d="M12 2V4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M12 20V22" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M4 12L2 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M22 12L20 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M19.7778 4.22266L17.5558 6.25424" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M4.22217 4.22266L6.44418 6.25424" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M6.44434 17.5557L4.22211 19.7779" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M19.7778 19.7773L17.5558 17.5551" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div className={`toggle-icon moon ${isDark ? 'fade-in' : 'fade-out'}`}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className={`toggle-thumb ${isDark ? 'dark' : 'light'}`}></div>
      </div>
    </button>
  );
};

export default ThemeToggle; 