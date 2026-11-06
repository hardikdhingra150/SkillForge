// Run before the Vercel build: a site built without VITE_API_BASE_URL would talk to http://127.0.0.1:8000 and
// fail for every visitor, so stop the build with a clear message instead.
const url = process.env.VITE_API_BASE_URL || "";
if (!/^https:\/\/.+\/api\/v1$/.test(url)) {
  console.error(
    "Set VITE_API_BASE_URL in Vercel (Project > Settings > Environment Variables) to your backend's address, "
    + "for example https://your-name-skillforge-api.hf.space/api/v1, then redeploy.",
  );
  process.exit(1);
}
console.log(`Building against ${url}`);
