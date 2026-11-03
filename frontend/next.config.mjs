/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [{
      protocol: 'https',
      hostname: 'whc.unesco.org',
      port: '',
      pathname: '/uploads/thumbs/**',
    }],
  },
}

export default nextConfig
