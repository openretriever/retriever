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
      head: [
        {
          tag: 'script',
          content: `
addEventListener('DOMContentLoaded', () => {
  const h1 = document.querySelector('h1#_top') || document.querySelector('.sl-markdown-content h1') || document.querySelector('main h1');
  if (!h1 || document.querySelector('.md-actions')) return;
  const path = location.pathname.replace(/^\\/+|\\/+$/g, '') || 'index';
  // Skip the splash/landing page — no source .md to view/copy there.
  if (path === 'index' || document.querySelector('.hero')) return;
  const raw = '/raw/' + path + '.md';
  const wrap = document.createElement('div');
  wrap.className = 'md-actions';
  const copy = document.createElement('button');
  copy.type = 'button'; copy.className = 'md-copy'; copy.textContent = 'Copy as Markdown';
  const view = document.createElement('a');
  view.className = 'md-view'; view.href = raw; view.target = '_blank'; view.rel = 'noreferrer'; view.textContent = 'View as Markdown';
  wrap.append(copy, view);
  h1.insertAdjacentElement('afterend', wrap);
  copy.addEventListener('click', async () => {
    try {
      const md = await (await fetch(raw)).text();
      await navigator.clipboard.writeText(md);
      const prev = copy.textContent; copy.textContent = 'Copied'; copy.classList.add('is-done');
      setTimeout(() => { copy.textContent = prev; copy.classList.remove('is-done'); }, 1400);
    } catch { window.open(raw, '_blank'); }
  });
});
`,
        },
      ],
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
            { label: 'Why Retriever', slug: 'concepts/why-retriever' },
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
          label: 'Notebooks',
          items: [
            { label: 'Flow Fundamentals', slug: 'notebooks/flow-fundamentals' },
            { label: 'Time and Sync', slug: 'notebooks/time-and-sync' },
            { label: 'Step, Debug, Replay', slug: 'notebooks/step-debug-replay' },
            { label: 'Standard Types', slug: 'notebooks/standard-types' },
            { label: 'Using the Hub', slug: 'notebooks/using-the-hub' },
          ],
        },
        {
          label: 'Retriever Hub',
          items: [
            { label: 'Ecosystem Overview', slug: 'ecosystem' },
            { label: 'GoldenRetriever Examples', slug: 'ecosystem/golden-packs' },
            { label: 'Hub Packs and Modules', slug: 'ecosystem/modules' },
            { label: 'Composable Pipelines', slug: 'ecosystem/composable-pipelines' },
            { label: 'Publishing', slug: 'ecosystem/publishing' },
          ],
        },
      ],
    }),
  ],
});
