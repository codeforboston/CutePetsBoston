# Instagram Debugging

Last reviewed: October 6, 2026.

These notes cover missing posts, checking credentials, and testing the Instagram connection. For account creation, Meta app settings, permissions, and token renewal, see [Meta account ecosystem](meta-account-ecosystem.md).

## Start with the failed run

Open GitHub Actions > Prod Account Post and inspect the relevant run. Read the Instagram-specific result in the logs and check the actual Instagram profile. A green workflow alone does not establish that every platform published successfully.

Production artifacts include `database.json`, `dashboard.html`, and `cutepets.log`; debug runs also save logs. The API error in `cutepets.log` helps distinguish authentication, permission, and media-processing problems. Preserve the failure message and relevant IDs, but redact credentials before sharing logs.

| Symptom | First checks |
| --- | --- |
| Credentials missing | Confirm both secrets exist and the selected workflow maps the intended account. |
| Authentication fails / invalid or expired token | Confirm expiry, revocation, account ID, and that the token came from Instagram Login for this app and account. Reauthorize if needed. |
| Permissions error | Compare authorized permissions, app roles, app mode, and access levels with the portal. Adding a permission may require renewed consent. |
| Wrong username returned | Stop publishing and correct the ID/token pair. |
| Account cannot be added in the portal | Confirm professional account type, accepted invitations, login access, and any portal verification prompts. |
| Image or container processing fails | Confirm the image URL is publicly retrievable by Meta and meets current publishing requirements. Inspect the API response in `cutepets.log`. |
| Metrics missing | Check the collector's error in logs and whether the media belongs to the account authorized by the token. |
| Workflow is green but no Instagram post | Read the platform result; individual failures can be logged without failing the entire workflow. |

## Check the connection without posting

### Debugging tools

Use the [Graph API Explorer](https://developers.facebook.com/tools/explorer?domain=INSTAGRAM&method=GET&path=me%3Ffields%3Did%2Cname&version=v26.0) to try API requests. This link opens the Instagram domain with a GET request for `me?fields=id,name` using API version `v26.0`.

Use the [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken) when investigating token issues.

### Local connection check

Load the intended account's ID and token into your local process environment using the team's credential procedure. The poster reads `INSTAGRAM_BUSINESS_ACCOUNT_ID` and `INSTAGRAM_PAGE_ACCESS_TOKEN`, including when testing locally. It does not read `INSTAGRAM_TEST_*` variables or automatically load `.env` files. Despite its name, the token variable holds an Instagram Login token in this implementation.

From the repository root, this command checks credentials without publishing:

```powershell
python -c "from social_posters.instagram import PosterInstagram; p = PosterInstagram(); ok = p.authenticate(); print('Authenticated:', ok, 'Username:', p.username); raise SystemExit(0 if ok else 1)"
```

Check that the returned username is the account you intended to use before running a publishing command. If authentication fails, resolve that before investigating image processing or captions.

## Preview and publish a test post

Preview the manual sample without authentication or publishing:

```powershell
python manual_testing/instagram_manual_test.py --dry-run
```

To publish a controlled post to the test account, load its credentials and use a publicly accessible image URL for which the project has permission:

```powershell
python manual_testing/instagram_manual_test.py --image-url "https://YOUR-PUBLIC-HOST/test-pet.jpg"
```

Replace the placeholder URL first. The script publishes a fictional sample pet caption; inspect the dry-run output before posting. It prints the authenticated username and polls container processing for up to 60 seconds. Inspect the post in Instagram and remove the sample if appropriate.

The poster creates a media container, waits for processing, then publishes it. With multiple images, it creates individual carousel items first. Authentication can succeed while a later media operation fails, so use the logged error to identify the stage.

## Test through GitHub Actions

Open Actions > Debug Post > Run workflow. This workflow uses the test-account secrets, mapped to the ordinary runtime variable names.

- Leave `debugposters` enabled for a preview without real social posts. Turning it off publishes to configured test accounts, including other platforms.
- `debugsources` chooses mock versus live pet data.
- Push-triggered Debug Post runs use debug sources and posters.

After production credential replacement, check the next production run and the Instagram profile. Running Prod Account Post manually may publish to all configured social accounts.

To pause scheduled publishing while investigating, disable **Prod Account Post** from its Actions workflow menu. This pauses the whole workflow, including the other platforms. Enable it again after resolving the issue.

## Maintenance and account restrictions

Check recent posts, the Instagram account's status, production workflow logs, and Meta developer alerts regularly. Follow the [token renewal notes](meta-account-ecosystem.md#access-tokens-and-why-they-need-attention) before credentials expire. When Meta announces an API version retirement, review `GRAPH_API_VERSION`, affected endpoints, and test-account behavior.

Using Meta's official API does not guarantee that an account cannot be restricted. If an account is restricted, review Instagram's account-status prompts and Meta's available appeal process. Add the symptoms and what resolved them to these notes so the next person has a useful starting point.
