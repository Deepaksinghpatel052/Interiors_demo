# Full-version roadmap (locked features)

Each locked teaser in the demo maps to one item below. Estimates assume the current Django codebase and one
developer; they are planning guides, not commitments. All items keep the white-label/feature-flag rules:
client-specific values in `StudioSettings`, a module flag per feature, no secrets in code.

| # | Feature | Technical approach | Effort |
|---|---|---|---|
| 1 | **3D / 360° walkthrough** | Accept equirectangular JPGs (from SketchUp/V-Ray/Enscape exports) per design version; view with a small viewer (Pannellum via CDN) in the case study and portal; hotspots stored as JSON (yaw/pitch → next room). Optional Matterport/Kuula embed field. | 3–4 days |
| 2 | **AR “view in your room”** | Product model with GLB + USDZ files; `<model-viewer>` web component (AR Quick Look on iOS, Scene Viewer on Android). Catalogue items get an optional 3D model. No app needed. | 3–5 days |
| 3 | **Online payments (Razorpay)** | Razorpay Orders API on invoice balance; Checkout in the portal; webhook (`payment.captured`, signature-verified) creates `Payment` and receipt PDF; idempotency by order/payment id; refunds via dashboard. Keys in `.env`. | 3–4 days |
| 4 | **Inventory & procurement** | Models: PurchaseOrder (+ lines from catalogue), GoodsReceipt, StockLocation (store/site), StockMove, VendorBill. PO PDF reusing the quotation PDF engine; project-wise material consumption vs. quotation. | 2–3 weeks |
| 5 | **Advanced accounting & Tally export** | Expense model with categories/receipts; project P&L (invoiced − expenses − PO cost); GST summary (GSTR-1 style CSV); Tally XML export of sales vouchers/receipts (Tally ERP 9 / Prime import format). | 1–2 weeks |
| 6 | **Attendance, payroll & contractors** | Attendance per site with geo-tagged check-in from the mobile web app; wage rates per worker/contractor; weekly payout sheet; contractor work orders and running bills; payment advice PDF. | 2 weeks |
| 7 | **WhatsApp Business API & campaigns** | Meta WhatsApp Cloud API (or a BSP like Gupshup/Interakt); approved templates mirrored from current `MessageTemplate`; the existing automation engine switches from “prepare” to “send” per template; delivery/read webhooks update `AutomationLog.status`; opt-out handling; broadcast lists with consent. | 1–2 weeks (+ Meta approval time) |
| 8 | **Instagram / Facebook lead ads sync** | Meta Lead Ads webhook (`leadgen`) → Graph API fetch → `Lead` with source = campaign; page subscription via a small OAuth connect screen in settings; dedupe by mobile. | 3–4 days |
| 9 | **Google Calendar two-way sync** | OAuth per designer; push bookings via Calendar API; incoming changes via push notifications (watch channels) with sync tokens; busy times block slots in `bookings.slots`. | 1 week |
| 10 | **Email campaigns** | Segments from leads/clients; templates with the brand; send via SES/SendGrid/Brevo API with batch + unsubscribe link; open/click tracking webhooks; consent field on leads. | 1 week |
| 11 | **Google review requests** | Automation rule 7 days after handover → WhatsApp/email with the studio's Google review link (Place ID in settings); track clicks with a redirect URL. | 1–2 days |
| 12 | **Advanced roles & multi-branch** | Replace the two groups with Role model + per-module permissions (view/edit/approve money); Branch FK on leads/projects/invoices with a branch switcher; per-branch numbering and GSTIN. | 1–2 weeks |
| 13 | **Mobile app for designers & supervisors** | First as an installable PWA (manifest + service worker, offline queue for site photos); later a Capacitor/React Native wrapper using a DRF API (token auth) for tasks, site updates, attendance. | PWA 1 week; native 3–4 weeks |
| 14 | **AI “Ask your business data”** | Text-to-query with **tool use**, not raw SQL: Claude calls a fixed set of safe, read-only functions (`leads_by_source(period)`, `overdue_invoices()`, `revenue(month)`…) scoped to the user's permissions; answers cite the numbers and link to the ERP page. | 1 week |

## Also planned (not teased in the demo)

- Hindi/regional language switch for the website and portal (Django i18n).
- SMS fallback (MSG91) for clients without WhatsApp.
- Backups to S3-compatible storage; Postgres for larger studios.
- Audit log of money changes.
