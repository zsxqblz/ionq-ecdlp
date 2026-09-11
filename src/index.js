const PREFIX = '/ionq-ecdlp';
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === PREFIX) {
      url.pathname += '/';
      return Response.redirect(url.toString(), 308);
    }
    if (!url.pathname.startsWith(PREFIX + '/')) return new Response('Not found', {status: 404});
    url.pathname = url.pathname.slice(PREFIX.length);
    const response = await env.ASSETS.fetch(new Request(url, request));
    const headers = new Headers(response.headers);
    const location = headers.get('Location');
    if (location) {
      const redirect = new URL(location, url);
      if (redirect.origin === url.origin) { redirect.pathname = PREFIX + redirect.pathname; headers.set('Location', redirect.toString()); }
    }
    headers.set('X-Content-Type-Options', 'nosniff');
    return new Response(response.body, {status: response.status, headers});
  }
};
