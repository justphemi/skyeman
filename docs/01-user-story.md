# 1. User Story — Skyeman Inc.

> A *user story* describes a feature from the perspective of the end user.
> It follows the format: **As a `<role>`, I want `<goal>`, so that `<benefit>`.**

---

## 1.1 Primary user stories (customer)

| # | As a… | I want to… | So that… |
|---|---|---|---|
| US-1 | **Guest visitor** | browse drop zones and packages without logging in | I can decide whether Skyeman is worth signing up for. |
| US-2 | **Guest visitor** | create an account with just my email, optional full name, and a password (no separate username) | I can book jumps and track my bookings. |
| US-3 | **Customer** | log in with either my email or my username + password | I don't have to remember which one I signed up with. |
| US-4 | **Customer** | see all available time slots for a chosen drop zone | I can pick a date and time that fits my schedule. |
| US-5 | **Customer** | book a jump by walking through a 4-step wizard (drop zone → package → time slot → my details) | I can secure a place on a jump without losing context. |
| US-6 | **Customer** | add companion jumper names and ages for a Group booking | everyone on my team gets a properly sized harness and waiver. |
| US-7 | **Customer** | see a clear confirmation after I book and "pay" | I know the booking is locked in. |
| US-8 | **Customer** | see all my bookings on a dashboard | I can keep track of upcoming and past flights. |
| US-9 | **Customer** | cancel a booking before the jump | I can get a refund if my plans change. |
| US-10 | **Customer** | reschedule a booking to a different open slot | I can recover from a schedule conflict without losing my money. |
| US-11 | **Customer** | edit my profile (name, email) | my information stays current. |

## 1.2 Admin user stories (operator)

The operator has two surfaces: the **Django admin** (`/admin/`) for full CRUD on
every model, and the **Operations Console** (`/manage/`) for a friendlier day-to-day
view with KPIs and quick actions.

| # | As a… | I want to… | So that… |
|---|---|---|---|
| US-12 | **Admin operator** | log in to the Django admin | I can manage every record in the system. |
| US-13 | **Admin operator** | see today's bookings, upcoming slots, and cancellations on a single dashboard | I can plan the day's operations at a glance. |
| US-14 | **Admin operator** | add a new drop zone with its address and description | I can expand the business into new locations. |
| US-15 | **Admin operator** | create or edit a jump package (price, age, weight, duration) | I can adjust offerings as the market changes. |
| US-16 | **Admin operator** | create time slots for a drop zone (date, start time, capacity) from the Slots Calendar | I can publish jump windows to customers. |
| US-17 | **Admin operator** | mark a slot as `full` or `cancelled (weather)` with one click | I can stop new bookings on a sold-out or unsafe day. |
| US-18 | **Admin operator** | search and filter bookings by customer, drop zone, status, and date | I can quickly find any booking. |
| US-19 | **Admin operator** | mark a payment as `paid`, `refunded`, or `failed` | I keep financial records in sync with reality. |
| US-20 | **Customer** | download my booking confirmation as a PNG or JPG ticket | I can show it at the drop zone and share it with friends. |
| US-21 | **Customer** | browse the site without seeing the marketing footer once I'm logged in | my dashboard stays focused on my bookings. |

---

## 1.3 One-line summary (the elevator pitch)

> **As a first-time skydiver**, I want to pick a drop zone, choose a package,
> pick an open time slot, enter my details (and my friends' for a group),
> and pay (simulated) — **so that** booking my jump takes four steps, not
> forty.

---

## 1.4 Acceptance criteria (selected examples)

**US-5 — Booking a slot**
- ✅ The customer must be logged in (signup is a 2-step wizard: email → password; no separate username field, no confirm-password field).
- ✅ The wizard has exactly four steps: drop zone, package, time slot, details.
- ✅ State flows via URL query params (`?dropzone=X&package=Y&slot=Z`) so the
  customer can bookmark and share links.
- ✅ The slot's `status` must be `open` and `seats_left > 0` at save time.
- ✅ The chosen package's `min_age` must be ≤ the customer's `jumper_age`.
- ✅ The chosen package's `max_weight_kg` must be ≥ the customer's `jumper_weight_kg`.
- ✅ On success, the customer is redirected to a checkout page and then a confirmation page.

**US-6 — Group companions**
- ✅ When `group_size > 1`, the wizard shows `group_size − 1` companion rows.
- ✅ Each companion captures `full_name` (required), `age` (required),
  `weight_kg` (optional).
- ✅ The lead jumper is auto-recorded from the logged-in user.
- ✅ The slot's `seats_left` decreases by `group_size` (not 1).

**US-13 — Admin dashboard**
- ✅ Visiting `/manage/` shows 8 KPI tiles: today's bookings, next 7 days,
  pending bookings, cancellations last 30 days, 30-day simulated revenue,
  total users, total drop zones, open slots this week.
- ✅ Below the KPIs, three tables show the 8 most recent bookings, the 8
  soonest upcoming slots, and the 5 most recent payments.

**US-16 — Slot calendar**
- ✅ `/manage/slots/` lists every slot grouped by date.
- ✅ A "+ New Slot" form lets staff create a slot in seconds.
- ✅ One-click buttons on each row: `Open` / `Mark full` / `Cancel` / `Delete`.

**US-20 — Booking ticket download**
- ✅ On a confirmed booking, the detail page shows two buttons: "Download ticket (PNG)" and "Download JPG".
- ✅ The PNG endpoint also serves SVG via `?format=svg`.
- ✅ Each ticket embeds the Skyeman brand mark, a `CONFIRMED` status pill, the jumper name, drop zone, package, date, time, group size, amount, and a unique reference like `SKY-000007`.

---

## 1.5 Seed command

The `python manage.py seed` command (also `--reset`) keeps the demo database
ready to use:

- Creates or refreshes the **admin user** — `admin@skyeman.com` / `Skyeman123!`
  (`is_staff=True`, `is_superuser=True`). Idempotent: re-running resets the
  password so the credentials are always usable.
- Creates 3 drop zones (Ikoyi Airfield, Lekki Coastal, Victoria Island Skyport).
- Creates 4 jump packages (Tandem ₦120,000 / AFF ₦220,000 / Solo ₦55,000 / Group ₦95,000).
- Creates 4 demo time slots spread across the next week, **including one slot
  with `capacity = 1`** at Lekki Coastal two days out — booking it once is
  enough to demonstrate the auto-flip-to-full behaviour.
