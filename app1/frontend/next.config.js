/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    poweredByHeader: false,
    env: {
      API_URL: process.env.API_URL || 'http://localhost:8000',
      WS_URL: process.env.WS_URL || 'ws://localhost:8000/ws',
    },
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.API_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ];
    },
    images: {
      domains: ['localhost'],
    },
  };
  
  module.exports = nextConfig;