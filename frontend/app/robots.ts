import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://coursepilot.vercel.app";
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/sign-in", "/sign-up"],
      disallow: ["/api/"],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
