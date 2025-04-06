# Trading Platform Frontend

A modern trading platform built with Next.js, TypeScript, and Tailwind CSS.

## Features

- Real-time market data updates via WebSocket
- Market and limit order placement
- Order management (view, cancel)
- User authentication
- Responsive design
- Real-time order updates

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Form Handling**: React Hook Form
- **Real-time Updates**: WebSocket
- **HTTP Client**: Axios
- **UI Components**: Custom components with Tailwind CSS
- **Notifications**: React Toastify

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Copy the environment variables:
   ```bash
   cp .env.example .env.local
   ```
4. Update the environment variables in `.env.local` with your configuration

### Development

Run the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Build

Create a production build:

```bash
npm run build
```

### Production

Start the production server:

```bash
npm start
```

## Project Structure

```
src/
├── components/        # React components
│   ├── layout/       # Layout components
│   └── trading/      # Trading-specific components
├── hooks/            # Custom React hooks
├── lib/              # Utility libraries
├── pages/            # Next.js pages
├── store/            # Zustand store
├── styles/           # Global styles
└── types/            # TypeScript types
```

## Components

### Layout
- `Layout.tsx`: Main layout wrapper with navigation

### Trading
- `MarketDataCard.tsx`: Displays real-time market data
- `OrdersTable.tsx`: Shows and manages orders
- `TradingForm.tsx`: Form for placing market/limit orders

## Custom Hooks

- `useTrade.tsx`: Trading functionality and market data
- `useMarketOrder.tsx`: Market order placement
- `useLimitOrder.tsx`: Limit order placement

## State Management

The application uses Zustand for state management:
- `auth.ts`: Authentication state and actions

## API Integration

- `api.ts`: Axios-based API client
- `websocket.ts`: WebSocket client for real-time updates

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |
| `NEXT_PUBLIC_JWT_COOKIE_NAME` | JWT cookie name | `trading_platform_token` |

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT