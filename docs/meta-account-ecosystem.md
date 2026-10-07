# Meta Account Ecosystem

Last reviewed: October 6, 2026.

These notes explain how CutePetsBoston's Instagram accounts, Meta developer app, access tokens, and scheduled posts fit together. The accounts are already running; the setup steps are here so anyone on the team can understand the connection and recreate it when needed. For connection checks, test posts, and troubleshooting, see [Instagram debugging](instagram-debugging.md).

## The pieces and how they fit together

An Instagram account is the public profile people follow. A Meta developer app is the configuration that lets our code use Meta's API. An access token is the credential that gives that app permission to act for a particular Instagram account. GitHub Actions runs our Python code on a schedule and supplies the account ID and token from repository secrets.

| Piece | What it does | Where to find it |
| --- | --- | --- |
| Instagram professional account | Owns the profile and published posts | Instagram app / account settings |
| Numeric Instagram API user ID | Tells the API which account to use | Meta's authorized account information |
| Meta developer app | Defines API configuration, permissions, and app roles | Meta for Developers > My Apps |
| Access token | Authorizes API requests for an account | Issued through Instagram Login; stored securely |
| GitHub Actions secrets | Supply credentials to scheduled runs | Repository Settings > Secrets and variables > Actions |
| Posting code | Formats pet posts and calls Instagram's API | `social_posters/instagram.py` |
| Workflow | Runs the project on a schedule or on demand | `.github/workflows/prod.yml` and `dev.yml` |

## Project accounts and personal Meta credentials

| Env | Account Handle | Email | Account Contact |
| --- | --- | --- | --- |
| Production | [@cutepetsboston](https://www.instagram.com/cutepetsboston/) | [cutepetsboston@codeforboston.org](mailto:cutepetsboston@codeforboston.org) | Harlan Weber |
| Test | [@cutepetsboston2026_test](https://www.instagram.com/cutepetsboston2026_test/) | [cutepetsboston@codeforboston.org](mailto:cutepetsboston@codeforboston.org) | Zachary Lowen |

Meta administration relies on real people's credentials. The personal Facebook profile used to administer the developer app should represent the actual person managing it. Meta's [authentic identity policy](https://about.fb.com/news/2023/09/you-can-now-have-multiple-personal-profiles-on-facebook/) requires a main Facebook profile to use the name the person goes by in everyday life. Team members should use their own authorized profiles and receive app or business roles rather than share someone's personal Facebook login.

The project's Instagram profiles can use the CutePetsBoston name. Instagram does not require a public real name, but does require accurate, current account information; see its [Community Guidelines](https://www.facebook.com/help/477434105621119?locale=en_GB). The real person administering Meta and the public project profile serve different purposes.

The Meta app name, app ownership, granted permissions, and token expiry dates still need to be checked in the portal. Keep passwords, tokens, app secrets, and recovery codes in the team's password manager; link to the record instead of copying credentials here.

## Which Instagram API we use

The current poster uses **Instagram API with Instagram Login**, calling `https://graph.instagram.com/v26.0`. This setup supports professional Instagram accounts (Creator or Business) and does not require a linked Facebook Page. Meta documents both login options in its [official Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-1ff01566-3509-48bd-a0f4-8571a91ccfdf).

Earlier project instructions described Facebook Login and Page access tokens. Those instructions do not describe the current implementation. Do not switch login products or generate a Facebook Page token just because an environment variable contains the word `PAGE`.

| Runtime variable | Actual meaning in this implementation |
| --- | --- |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Numeric Instagram API user ID for the authorized professional account, including a Creator account. It is not the username. |
| `INSTAGRAM_PAGE_ACCESS_TOKEN` | Instagram access token issued for the Instagram Login flow. The name is retained from the older integration. |

`social_posters/instagram.py` sends the token as a Bearer authorization header. It checks the account's ID and username, creates photo or carousel containers, waits for processing, and publishes them. `metric_collectors/instagram.py` uses the same token to read media like and comment counts.

**TODO**: No token refresh automation is present in the checked repository. Someone needs to renew the credentials, unless the team has a separate process outside this repo.

## Creating an Instagram account

For a new test or project account, the relevant steps are:

1. Create the Instagram account using an email address the project can continue to access. Give test accounts a clearly identifiable username and bio.
2. Confirm the email address and account recovery details. Save the credentials and recovery codes in the team's password manager.
3. In Instagram settings, find the account type / professional account options and switch to a Creator or Business account. Menu labels can change; confirm the resulting account type in settings.
4. Set the profile image, bio, and project website. For a test account, make clear that sample posts are tests.
5. Enable two-factor authentication and make sure the team knows how account access and recovery work.
6. Check that the account can sign in normally and has no unresolved account-status or verification prompts before authorizing it in Meta.

A Facebook Page may still be useful for the project's Facebook presence. If desired, create a project Page from a real administrator's Facebook profile and connect Instagram through the Page's Linked accounts settings or Meta Business Suite. Record who has Page access. This optional link is separate from the Instagram Login credentials used by this code.

## Finding your way around the Meta developer portal

Start at [Meta for Developers: My Apps](https://developers.facebook.com/apps/) using your own authorized administrator account. If the project app is missing, an existing administrator may need to invite you to the app or its business portfolio. Access to the Instagram profile and access to the developer app are separate things.

The Meta app ID identifies the developer app; the Instagram API user ID identifies the Instagram account. They are different IDs. Test and production may share an app, but the repository alone does not establish whether they do.

The dashboard labels vary by app and Meta's current interface. Locate these areas by their purpose:

| Portal area | What to manage |
| --- | --- |
| App settings / Basic | App ID, contact email, required policy URLs, and app ownership. App secrets belong in the password manager. |
| App roles / Roles | Administrators, developers, and testers; invitations need to be accepted before access works. |
| Instagram use case / API setup with Instagram login | Connect professional accounts, authorize access, and generate account tokens where that option is available. |
| App Review / Permissions and Features | Permission access levels, review status, and requested evidence. |
| Dashboard / alerts / required actions | Platform notices, data-use checkups, verification requests, and deadlines. |
| API version settings | Version lifecycle notices; coordinate changes with the version constant in the code. |

To create an app from scratch:

1. Register for Meta developer access using the volunteer's own Facebook account, completing any required verification.
2. Choose Create App and the use case that supports managing Instagram professional accounts. If Meta asks for an app type or business portfolio, choose the option appropriate to the project's ownership and Instagram Login support.
3. Give the app a recognizable project name and a monitored contact email. Record its ID and owner.
4. Configure **Instagram API with Instagram Login**. Follow the [official setup documentation](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/); avoid the Facebook Login setup for this implementation.
5. Connect the professional test account through the portal's supported account authorization / token generation flow. If Meta requires an Instagram tester role, invite the relevant account, then follow the acceptance steps below before retrying authorization.
6. Enable and authorize the permissions needed by this flow: `instagram_business_basic` and `instagram_business_content_publish`. Meta lists publishing access in its [official publishing collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-15c537cd-a773-4b40-a87c-27829e49a439). Check the current documentation if adding features beyond the repository's existing publishing and media-field reads.
7. Validate the test account before connecting production.

App mode, account roles, and permission access level determine who can authorize the app. Follow the portal's requirements for the intended accounts. If onboarding accounts outside the app's permitted roles requires Advanced Access or App Review, complete that process with the required policy URLs and a demonstration of the actual use case. Do not assume toggling the app to Live grants missing permissions.

### Accepting an Instagram tester invitation

Sending the request from Meta's developer portal is only the first part. The user must go into the invited Instagram account itself to accept it.

1. Sign into Instagram as the account that was invited. If you manage several accounts, switch to the invited profile first.
2. Open Instagram settings and find **Website permissions > Apps and websites > Tester invites**. Depending on the interface, **Apps and websites** may appear directly in settings; using Instagram in a browser is another way to find it.
3. Find the invitation for the project's Meta app and choose **Accept**.
4. Return to the Meta developer portal, refresh the account / tester list, and retry connecting the account or generating its token.

If the invitation is missing, check that the username in the developer portal matches the account currently signed into Instagram. Adding the account in Meta does not automatically accept the request, and being an app administrator does not accept an Instagram account's invitation on its behalf.

## Access tokens and why they need attention

An access token authorizes the application to act for an Instagram account. Anyone holding a usable token may be able to exercise its granted permissions. Keep it in the password manager and GitHub Actions secrets.

For an existing app, use its Instagram Login setup to authorize the intended account and obtain a token. Confirm the account and app before saving it. Obtain the numeric API user ID from the authorized account information, then validate it using the [read-only connection check](instagram-debugging.md#check-the-connection-without-posting).

For a custom OAuth flow, Meta documents authorization, code exchange, and long-lived tokens in [Instagram business login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/). Long-lived Instagram tokens generally last 60 days; eligible unexpired tokens can be refreshed after they are at least 24 hours old. Use Meta's current [refresh endpoint documentation](https://developers.facebook.com/docs/instagram-platform/reference/refresh_access_token/) to confirm eligibility and parameters before implementing a renewal process. Record the actual expiry returned by Meta; do not assume that a portal-generated token lasts indefinitely.

Token maintenance procedure:

1. Record the token's actual expiry, owning app, authorized account, and permissions in the password manager record.
2. Arrange a maintenance reminder comfortably before expiry, for example two weeks before, and agree who will handle it.
3. Refresh the token through the documented Instagram flow while it remains eligible, or reauthorize the account if renewal is unavailable or the token has expired.
4. Save the returned token securely and update the matching GitHub secret. If the account itself changes, update the account ID as well.
5. Run the read-only authentication check and confirm the returned username.
6. Verify a controlled test post and then the next scheduled production post. Record the new expiry and next maintenance date.

Password changes, revoked app access, account changes, or security actions may invalidate credentials before their recorded expiry. A refresh schedule does not replace checking posting results.

## How credentials reach GitHub Actions

In the repository, open Settings > Secrets and variables > Actions. The existing workflows expect repository secrets with these exact names:

| GitHub secret | Used by | Meaning |
| --- | --- | --- |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Prod Account Post | Production numeric Instagram API user ID |
| `INSTAGRAM_PAGE_ACCESS_TOKEN` | Prod Account Post | Production Instagram Login token |
| `INSTAGRAM_TEST_BUSINESS_ACCOUNT_ID` | Debug Post | Test numeric Instagram API user ID |
| `INSTAGRAM_TEST_PAGE_ACCESS_TOKEN` | Debug Post | Test Instagram Login token |

The Debug Post workflow maps test secrets to the ordinary runtime variable names. The Python poster does not read the `INSTAGRAM_TEST_*` names directly. For a local test, explicitly load test values into `INSTAGRAM_BUSINESS_ACCOUNT_ID` and `INSTAGRAM_PAGE_ACCESS_TOKEN` in the process environment. The scripts do not automatically load `.env` files.

GitHub does not reveal saved secret values. Use the password manager to preserve the credential record and replace a secret when needed.

The production workflow in `.github/workflows/prod.yml` runs every four hours on its UTC cron schedule and can also be dispatched manually. Running it may publish to all configured social accounts. To pause scheduled publishing, disable **Prod Account Post** from its Actions workflow menu; enable it again after the issue is resolved. This pauses the whole workflow, including the other platforms.

## Things that are easy to mix up

- An Instagram username, an Instagram API user ID, and a Meta app ID identify different things.
- The secret named `INSTAGRAM_PAGE_ACCESS_TOKEN` currently holds an Instagram Login token. Its name reflects an older implementation.
- A test Instagram profile is a real profile used for testing. Calling it a test account does not automatically give it access to a Meta app; authorization and any required role invitations still matter.
- Being able to sign into Instagram does not mean you can administer the Meta developer app or edit GitHub secrets.
- App roles, permission access levels, and Development/Live mode affect different parts of access. Switching modes does not grant permissions by itself.
- A successful GitHub workflow can still contain an Instagram posting failure. Look at the platform result and the actual profile.
- Removing a team member's Meta access may affect credentials they authorized. Check that dependency and replace credentials when needed.

As we learn more about the working setup, add the app name, account IDs, where credential records live, renewal process, and any portal quirks here. Notes about what actually happened are especially useful when Meta's interface changes.

## References and verification notes

- [Meta developer apps](https://developers.facebook.com/apps/)
- [Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/)
- [Instagram business login and token flow](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/)
- [Refresh an Instagram access token](https://developers.facebook.com/docs/instagram-platform/reference/refresh_access_token/)
- [Meta's official Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-1ff01566-3509-48bd-a0f4-8571a91ccfdf)

Repository behavior was checked against the current poster, metric collector, manual test script, and workflows. Meta's public documentation was consulted, but some developer pages required login or returned rate limits. Exact portal labels, existing app settings, granted permissions, ownership, and token lifetimes must be confirmed by an authorized administrator in the live portal. Recheck these instructions when Meta changes its setup flow.
