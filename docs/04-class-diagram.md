# 4. Class Diagram — Skyeman Inc.

> A *class diagram* shows the static structure of the system: classes, their
> attributes, methods, and the relationships between them. Below is the diagram
> for the Skyeman domain, followed by descriptions of each class and its
> relationships.

> Skyeman runs with a single instructor — **Femi**. There is no `Instructor`
> model and no `Instructor` table. The name surfaces only as
> `INSTRUCTOR_NAME = "Femi"` in `dropzones/models.py` for use in marketing copy.
> Every `TimeSlot` is run by Femi.

---

## 4.1 Diagram

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    direction LR

    class User {
      <<Django built-in>>
      +username: str
      +email: str
      +first_name: str
      +last_name: str
      +is_staff: bool
      +set_password()
      +check_password()
    }

    class DropZone {
      +name: str
      +city: str
      +address: str
      +description: text
      +image_url: str
      +upcoming_slots_count (property)
      +__str__()
    }

    class JumpPackage {
      +name: str (Tandem/AFF/Solo/Group)
      +price: decimal
      +description: text
      +min_age: int
      +max_weight_kg: int
      +duration_minutes: int
      +image_url: str
      +__str__()
    }

    class TimeSlot {
      +date: date
      +start_time: time
      +capacity: int
      +status: str (open/full/cancelled)
      +booked_count (property)
      +seats_left (property)
      +is_available (property)
      +update_status()
      +__str__()
    }

    class Booking {
      +status: str (pending/confirmed/cancelled/completed)
      +created_at: datetime
      +jumper_age: int
      +jumper_weight_kg: int
      +group_size: int
      +notes: text
      +total_price (property)
      +is_cancellable (property)
      +is_reschedulable (property)
    }

    class BookingParticipant {
      +full_name: str
      +age: int
      +weight_kg: int (nullable)
      +is_lead: bool
      +__str__()
    }

    class Payment {
      +amount: decimal
      +method: str (card/paypal)
      +status: str (pending/paid/refunded/failed)
      +paid_at: datetime
      +__str__()
    }

    DropZone "1" o-- "many" TimeSlot : hosts
    JumpPackage "1" o-- "many" Booking : selected_for
    DropZone "1" o-- "many" Booking : booked_at (via TimeSlot)
    TimeSlot "1" o-- "many" Booking : reservations
    User "1" o-- "many" Booking : owns
    Booking "1" --o "many" BookingParticipant : has
    Booking "1" --o "1" Payment : has (1:1)
```

---

## 4.2 Class descriptions

### 4.2.1 `User` *(Django built-in, used as-is)*
The platform's identity. The app relies on Django's auth user for sign-up,
log-in, sessions, and admin access. We extended `SignUpForm` and `ProfileForm`
to collect first/last name and email.

### 4.2.2 `DropZone`
A physical skydiving location (airfield + landing zone).
- **Attributes:** `name`, `city`, `address`, `description`, `image_url`.
- **Computed property:** `upcoming_slots_count` (count of future slots with
  `status='open'`).
- **Relationships:** Has many `TimeSlot`s.
- **Seed:** 3 rows are seeded — Ikoyi Airfield, Lekki Coastal, Victoria Island
  Skyport.

### 4.2.3 `JumpPackage`
A skydiving offering (Tandem, AFF, Solo, or Group).
- **Attributes:** `name` (unique, chosen from `PACKAGE_CHOICES`),
  `price` (Decimal Naira), `description`, `min_age`, `max_weight_kg`,
  `duration_minutes`, `image_url`.
- **Relationships:** Has many `Booking`s.
- **Eligibility** is enforced via the booking form
  (`BookingDetailsForm.clean()`).
- **Seed:** 4 rows are seeded — Tandem ₦120,000 / AFF ₦220,000 / Solo ₦55,000
  / Group ₦95,000.

### 4.2.4 `TimeSlot`
A scheduled jump window at a drop zone.
- **Attributes:** `date`, `start_time`, `capacity` (default 8),
  `status` (open / full / cancelled (weather)). FK to `DropZone`.
- **Computed properties:**
  - `booked_count` — non-cancelled bookings count.
  - `seats_left` — `max(0, capacity − booked_count)`.
  - `is_available` — `status=='open'` AND `seats_left > 0` AND slot is in the
    future (timezone-aware).
- **Method:** `update_status()` — auto-flips to `full` when capacity is
  reached, and back to `open` when a booking is cancelled.
- **Relationships:** Belongs to one `DropZone`. Has many `Booking`s.
- **Constraint:** `unique_together = (drop_zone, date, start_time)` — prevents
  the same slot being created twice at the same drop zone.
- **Seed:** **Not seeded.** Admins create slots via `/manage/slots/new/` or
  Django admin.

### 4.2.5 `Booking`
The user's reservation of a slot, with eligibility and group details captured
at booking time.
- **Attributes:** `status` (pending / confirmed / cancelled / completed),
  `created_at`, `jumper_age`, `jumper_weight_kg`, `group_size`,
  `notes`. FKs to `User`, `TimeSlot`, `JumpPackage`.
- **Computed properties:**
  - `total_price` — `package.price × group_size`, with a 10% discount when
    `package.name == "Group"` AND `group_size >= 3`.
  - `is_cancellable` / `is_reschedulable` — slot in future AND status in
    `('pending', 'confirmed')`.
- **Relationships:** Belongs to one `User`, one `TimeSlot`, one `JumpPackage`.
  Has many `BookingParticipant`s. Has one `Payment` (1:1).

### 4.2.6 `BookingParticipant`
A single jumper in a (potentially group) booking. Captures name, age, and
optional weight. One row per jumper — the lead jumper is flagged
`is_lead=True`; companions are `is_lead=False`.
- **Attributes:** `full_name`, `age`, `weight_kg` (nullable),
  `is_lead`.
- **Relationships:** Belongs to one `Booking`.
- **Wizard behaviour:** When `group_size > 1`, the wizard renders
  `group_size − 1` companion rows. When `group_size == 1`, only the lead
  jumper row is created from `request.user`.

### 4.2.7 `Payment`
The (simulated) payment for a booking.
- **Attributes:** `amount`, `method` (card / paypal), `status`
  (pending / paid / refunded / failed), `paid_at`.
- **Relationships:** 1:1 with `Booking`. Created/updated by the payment view
  when the user clicks "Pay now", and updated to `refunded` when a paid
  booking is cancelled.

---

## 4.3 Relationship summary

| From | Cardinality | To | Description |
|---|---|---|---|
| `DropZone` | 1 → * | `TimeSlot` | A drop zone hosts many time slots. |
| `JumpPackage` | 1 → * | `Booking` | A package can be the basis of many bookings. |
| `TimeSlot` | 1 → * | `Booking` | A time slot can be reserved by many bookings (up to capacity). |
| `User` | 1 → * | `Booking` | A user can have many bookings. |
| `Booking` | 1 → * | `BookingParticipant` | A booking has 1 lead participant + (group_size − 1) companions. |
| `Booking` | 1 ↔ 1 | `Payment` | A booking has exactly one (simulated) payment. |

---

## 4.4 Design notes

- **`on_delete=PROTECT` on `Booking.{time_slot, package}`** — prevents an admin
  from accidentally deleting a slot or package that has historical bookings.
- **`on_delete=CASCADE` on `Booking.participants` and `Booking.payment`** — when
  a booking is deleted, its participants and payment are cleaned up with it.
- **`unique_together = (drop_zone, date, start_time)` on `TimeSlot`** — one
  slot per drop zone per start time. The instructor field that used to be in
  the constraint is gone.
- **Status is a `CharField` with choices** rather than a separate `Status`
  model — keeps things readable for a uni assignment while still constrained.
- **Computed properties on `TimeSlot`** (`booked_count`, `seats_left`,
  `is_available`) keep the capacity logic in one place — used by views, admin,
  and the booking wizard.
- **`TimeSlot.update_status()`** is called after every booking, cancel, and
  reschedule so the `status` field never drifts from `booked_count`.
- **Single-instructor model** — `INSTRUCTOR_NAME = "Femi"` lives as a
  constant in `dropzones/models.py` for marketing copy only. There is no
  `Instructor` model, FK, admin screen, or migration.
