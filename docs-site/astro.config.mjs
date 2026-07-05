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
      sidebar: [
        {
          label: 'Start',
          items: [
            { label: 'Overview', link: '/' },
            { label: 'Visual Quickstart', slug: 'getting-started/visual-quickstart' },
            { label: 'Install', slug: 'getting-started/install' },
            { label: 'Landing', link: 'https://openretriever.org/' },
            { label: 'Continue: Golden Examples', link: 'https://retriever-space.pages.dev/examples/' },
            { label: 'Agent Map', link: '/llms.txt' },
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
            { label: 'Golden Hub Proof', slug: 'ecosystem/golden-packs' },
            { label: 'Hub Packs and Modules', slug: 'ecosystem/modules' },
            { label: 'Composable Pipelines', slug: 'ecosystem/composable-pipelines' },
            { label: 'Publishing', slug: 'ecosystem/publishing' },
          ],
        },
      ],
    }),
  ],
});
