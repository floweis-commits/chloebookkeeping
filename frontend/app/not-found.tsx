export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <p className="text-2xl font-light text-gray-400 mb-2">404</p>
        <p className="text-gray-500">Page not found.</p>
        <a href="/dashboard" className="mt-4 block text-sm text-blush-500 hover:underline">
          Go home
        </a>
      </div>
    </div>
  );
}
