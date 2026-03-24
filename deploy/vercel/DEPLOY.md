# Vercel Frontend + Render Backend

This project does not have a separate React/Vite/Next frontend. The UI is still rendered by Django templates, so the clean deployment path is:

- Vercel handles the public frontend URL.
- Vercel rewrites every request to your Render Django app.
- Render keeps serving the HTML, API responses, auth, and payments.

## 1. Create the Vercel rewrite

1. Copy `deploy/vercel/vercel.json.example` to the project root as `vercel.json`.
2. Replace `https://your-render-service.onrender.com` with your real Render backend URL.

Your final root `vercel.json` should look like this:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/:path*",
      "destination": "https://YOUR-RENDER-APP.onrender.com/:path*"
    }
  ]
}
```

## 2. Deploy the repo to Vercel

1. Push the repo to GitHub.
2. Import the repo into Vercel.
3. Use the default "Other" framework detection.
4. Leave build/output settings empty unless Vercel asks for something project-specific.
5. Deploy and note the generated Vercel domain.

## 3. Update Render environment variables

Use `deploy/vercel/render.env.example` as the template for your Render service.

Most important values:

- `DJANGO_ALLOWED_HOSTS` must include both the Render host and the Vercel host.
- `DJANGO_CSRF_TRUSTED_ORIGINS` must include both `https://...onrender.com` and `https://...vercel.app`.
- `PUBLIC_APP_BASE_URL` should be your Vercel URL.
- `PUBLIC_API_BASE_URL` should also be your Vercel URL when using the full Vercel rewrite proxy.

Then redeploy Render.

## 4. Smoke test

Test these flows through the Vercel URL only:

- Home page
- Explore page
- Movie detail page
- Login/signup
- Seat selection
- Checkout and payment success page
- My bookings
- Admin dashboard

## Notes

- If you want a true standalone frontend on Vercel, this repo would need a bigger refactor into a separate frontend app plus API-only backend endpoints.
- The current repo is now prepared for the proxy approach, which is the fastest way to keep the backend on Render and put the user-facing site on Vercel.
