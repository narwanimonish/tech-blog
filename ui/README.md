# Tech Blog UI

React + Vite SPA for the tech-blog API.

## Local development

1. Install dependencies:

   ```bash
   cd ui
   npm install
   ```

2. Point the app at your API (either option):

   - Edit `public/config.json`:

     ```json
     { "apiUrl": "https://YOUR_API.execute-api.us-east-1.amazonaws.com/dev" }
     ```

   - Or set an env var when starting Vite:

     ```bash
     VITE_API_URL=https://YOUR_API.execute-api.us-east-1.amazonaws.com/dev npm run dev
     ```

3. Start the dev server:

   ```bash
   npm run dev
   ```

Open http://localhost:5173 and sign in with a Cognito user (email + password).

## Features

| Page | API calls |
|------|-----------|
| Login | `POST /auth/login` |
| Posts | `GET/POST /posts`, `GET/PUT/DELETE /posts/{postId}` |
| Users | `GET /users`, `GET/PUT/DELETE /users/{userId}`, `PUT /users/{userId}/role` |

Role-based UI:

- **reader** — view posts and users
- **writer** — create/edit/delete posts
- **admin** — manage users, roles, and deletions

## Production (CloudFront)

CI/CD builds `ui/dist` and CDK deploys it via **TechBlogFrontendStack** (S3 + CloudFront).

At deploy time, CDK uploads a `config.json` with the live **ApiUrl** so the SPA does not need a rebuild when the API endpoint changes.

After deploy, get the site URL:

```bash
aws cloudformation describe-stacks \
  --stack-name TechBlogFrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" \
  --output text
```
