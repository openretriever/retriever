import type { APIRoute, GetStaticPaths } from 'astro';
import { getCollection } from 'astro:content';

// Raw-markdown endpoints for every docs page: /raw/<id>.md
// Powers the "Copy / View as Markdown" control (agent- and LLM-friendly).
export const getStaticPaths: GetStaticPaths = async () => {
  const docs = await getCollection('docs');
  return docs.map((entry) => ({ params: { slug: entry.id }, props: { entry } }));
};

export const GET: APIRoute = ({ props }) => {
  const entry = (props as { entry: { data: { title?: string }; body?: string } }).entry;
  const title = entry.data?.title ? `# ${entry.data.title}\n\n` : '';
  return new Response(title + (entry.body ?? ''), {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
};
