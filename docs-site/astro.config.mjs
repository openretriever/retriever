// @ts-check
import starlight from '@astrojs/starlight';
import { defineConfig } from 'astro/config';
import starlightThemeNova from 'starlight-theme-nova';

export default defineConfig({
  site: 'https://openretriever-docs.pages.dev',
  integrations: [
    starlight({
      title: 'Retriever',
      description: 'Build closed-loop robot agents with explicit time.',
      logo: {
        src: './src/assets/retriever-illustrative.jpeg',
        alt: 'Retriever',
      },
      favicon: '/assets/logo.svg',
      customCss: ['./src/styles/retriever.css'],
      plugins: [starlightThemeNova()],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/openretriever/retriever' },
      ],
      editLink: {
        baseUrl: 'https://github.com/openretriever/retriever/edit/main/docs-site',
      },
      sidebar: [
        {
          label: 'Start',
          items: [
            { label: 'Overview', link: '/' },
            { label: 'Visual Quickstart', slug: 'getting-started/visual-quickstart' },
            { label: 'Install', slug: 'getting-started/install' },
          ],
        },
        {
          label: 'Core Concepts',
          items: [
            { label: 'Flow', slug: 'concepts/flow' },
            { label: 'Time and Sync', slug: 'concepts/time-and-sync' },
            { label: 'Runtime', slug: 'concepts/runtime' },
            { label: 'Standard Types', slug: 'concepts/standard-types' },
            { label: 'Concepts and Lineage', slug: 'concepts/lineage' },
          ],
        },
        {
          label: 'Tutorial Path',
          items: [
            { label: 'Tutorial Overview', slug: 'tutorials' },
            { label: 'Examples and Results', slug: 'tutorials/examples-and-results' },
            { label: 'Debug and Visualize', slug: 'tutorials/debug-and-visualize' },
          ],
        },
        {
          label: 'Retriever Hub',
          items: [
            { label: 'Ecosystem Overview', slug: 'ecosystem' },
            { label: 'Modules', slug: 'ecosystem/modules' },
            { label: 'Composable Pipelines', slug: 'ecosystem/composable-pipelines' },
            { label: 'Publishing', slug: 'ecosystem/publishing' },
          ],
        },
      ],
    }),
  ],
});
