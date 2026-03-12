/** @type {import('next').NextConfig} */
const nextConfig = {
    // ── Standalone output for minimal Docker image ───────────────────────────
    output: 'standalone',

    // ── React strict mode catches subtle bugs ────────────────────────────────
    reactStrictMode: true,

    // ── Image optimization ────────────────────────────────────────────────────
    images: {
        domains: [
            'supabase.co',
            'res.cloudinary.com',
            'graph.instagram.com',
            'cdninstagram.com',
            'scontent.cdninstagram.com',
        ],
        formats: ['image/avif', 'image/webp'],
        minimumCacheTTL: 3600,
    },

    // ── Security headers ──────────────────────────────────────────────────────
    async headers() {
        return [
            {
                source: '/(.*)',
                headers: [
                    { key: 'X-DNS-Prefetch-Control', value: 'on' },
                    { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
                    { key: 'X-Content-Type-Options', value: 'nosniff' },
                    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
                    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
                ],
            },
        ];
    },

    // ── Webpack (suppress common warnings) ────────────────────────────────────
    webpack(config) {
        config.resolve.fallback = { fs: false, net: false, tls: false };
        return config;
    },

    // ── Compress responses ────────────────────────────────────────────────────
    compress: true,

    // ── Power header removal ──────────────────────────────────────────────────
    poweredByHeader: false,

    // ── Env vars available in browser ─────────────────────────────────────────
    env: {
        NEXT_PUBLIC_APP_VERSION: process.env.APP_VERSION || '2.0.0',
    },
};

module.exports = nextConfig;