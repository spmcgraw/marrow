import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://docs.marrow.so",
  integrations: [
    starlight({
      title: "Marrow",
      description:
        "Self-hosted, open-source knowledge base built around a non-negotiable restore guarantee.",
      editLink: {
        baseUrl: "https://github.com/spmcgraw/marrow/edit/main/docs/",
      },
      sidebar: [
        {
          label: "Getting started",
          items: [
            { label: "Overview", link: "/" },
            { label: "Quickstart", link: "/getting-started/quickstart/" },
          ],
        },
        {
          label: "Deployment",
          items: [
            { label: "Docker Compose", link: "/deployment/docker-compose/" },
            { label: "Cloudflare", link: "/deployment/cloudflare/" },
          ],
        },
        {
          label: "Configuration",
          items: [
            { label: "Environment variables", link: "/configuration/env-vars/" },
            { label: "OIDC authentication", link: "/configuration/oidc/" },
          ],
        },
        {
          label: "Concepts",
          items: [
            { label: "Restore guarantee", link: "/concepts/restore-guarantee/" },
            { label: "Export bundle format", link: "/concepts/export-format/" },
          ],
        },
      ],
    }),
  ],
});
