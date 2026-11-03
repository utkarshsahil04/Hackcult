/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: ['thumb.wikimedia.org', 'upload.wikimedia.org'].map((hostname) => ({
      protocol: 'https',
      hostname,
      port: '',
      pathname: '/wikipedia/commons/**',
    })),
  },
}

export default nextConfig
