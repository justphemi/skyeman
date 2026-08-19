# 3. Sequence Diagram — Skyeman Inc.

> A *sequence diagram* shows the order of messages exchanged between objects (or actors + system components) to carry out a use case. Time flows top → bottom.

The most important flow in the system is **booking a slot + simulated payment**,
which is now a 4-step wizard, so the diagram below focuses on that. Shorter flows
(sign-up, cancel, reschedule, admin slot calendar) are summarised at the end.

> Skyeman has a single instructor — Femi. There is no `Instructor` entity in
> any of these flows; the customer's wizard never asks "which instructor?"

---

## 3.1 Booking wizard + simulated payment

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor C as Customer
    participant V as Browser (UI)
    participant W1 as Step 1 View<br/>(pick drop zone)
    participant W2 as Step 2 View<br/>(pick package)
    participant W3 as Step 3 View<br/>(pick time slot)
    participant W4 as Step 4 View<br/>(details)
    participant F as BookingDetailsForm
    participant TS as TimeSlot (DB)
    participant Pkg as JumpPackage (DB)
    participant DZ as DropZone (DB)
    participant B as Booking (DB)
    participant BP as BookingParticipant (DB)
    participant PV as Payment View
    participant Pay as Payment (DB)
    participant CV as Confirmation View

    %% Step 1
    C->>V: Click "Book a jump"
    V->>W1: GET /bookings/book/step-1/
    W1->>DZ: list drop zones
    DZ-->>W1: zones
    W1-->>V: Render radio cards
    C->>V: Pick a drop zone
    V->>W2: POST ?dropzone=X → redirect

    %% Step 2
    V->>W2: GET /bookings/book/step-2/?dropzone=X
    W2->>DZ: load zone
    W2->>Pkg: list packages
    W2-->>V: Render package cards
    C->>V: Pick a package
    V->>W3: POST ?dropzone=X&package=Y → redirect

    %% Step 3
    V->>W3: GET /bookings/book/step-3/?dropzone=X&package=Y
    W3->>TS: list open future slots at zone with seats_left > 0
    TS-->>W3: slots
    W3-->>V: Render date-grouped slot grid
    C->>V: Pick a slot
    V->>W4: POST ?dropzone=X&package=Y&slot=Z → redirect

    %% Step 4
    V->>W4: GET /bookings/book/step-4/?...&slot=Z
    W4->>TS: re-check is_available + seats_left
    alt Slot no longer available
        W4-->>V: Redirect back to step 3 with error
    else Slot still available
        W4-->>V: Render details form (age, weight, group_size, companions)
        C->>V: Submit details + companions
        V->>W4: POST step-4 form
        W4->>F: Validate (capacity, age, weight, companions)
        alt Form invalid
            F-->>W4: ValidationError
            W4-->>V: Re-render with errors
        else Form valid
            W4->>B: INSERT Booking (status=pending)
            W4->>BP: INSERT lead BookingParticipant (user)
            loop For each companion
                W4->>BP: INSERT BookingParticipant (name, age, weight)
            end
            W4->>TS: update_status (auto-full if now exhausted)
            W4-->>V: Redirect to /bookings/<id>/pay/
        end
    end

    %% Payment
    C->>V: Click "Pay now"
    V->>PV: POST /bookings/<id>/pay/  {method}
    PV->>B: load booking
    PV->>Pay: UPSERT (status=paid, amount=total_price, paid_at=now)
    PV->>B: UPDATE status=confirmed
    PV->>TS: update_status
    PV-->>V: Redirect to /bookings/<id>/confirmation/
    V->>CV: GET /bookings/<id>/confirmation/
    CV->>B: load booking + payment + participants
    CV-->>V: Render confirmation page
    V-->>C: Show "You're booked!" + summary
```

---

## 3.2 Step-by-step description

1. **Customer clicks "Book a jump."** Browser sends `GET /bookings/book/step-1/`. The view loads the seeded drop zones and renders them as radio cards.
2. **Step 1 submit.** Customer picks a drop zone. View returns a 302 to `/bookings/book/step-2/?dropzone=X`.
3. **Step 2 — pick package.** Customer picks a `JumpPackage`. View returns a 302 to step 3 with both query params.
4. **Step 3 — pick time slot.** View lists future `TimeSlot`s at the chosen drop zone with `status='open'` and `seats_left > 0`, grouped by date.
5. **Step 4 — jumper details.** View re-checks the slot's availability (a slot could have been booked out by another user mid-wizard). If still available, it renders the form with hidden companion rows (rendered server-side from `BookingDetailsForm.companion_forms`).
6. **Step 4 submit.** `BookingDetailsForm.clean()` enforces:
   - `slot.seats_left >= group_size`
   - `jumper_age >= package.min_age`
   - `jumper_weight_kg <= package.max_weight_kg`
   - `package.name == "Group"` ⇒ `group_size >= 2`
   - every companion row valid (name + age 16-100)
7. **Booking + participants are inserted** as one atomic transaction. Lead jumper is created from `request.user`. Each companion becomes a `BookingParticipant`.
8. **Slot auto-flips to `full`** via `TimeSlot.update_status()` if its `booked_count` now reaches `capacity`.
9. **Customer redirected** to `/bookings/<id>/pay/`.
10. **Payment.** `PaymentForm` is shown. On submit, `Payment` is upserted with `status='paid'`, `Booking.status='confirmed'`, and `TimeSlot.update_status()` runs again.
11. **Confirmation page** renders a summary card and acts as the stand-in for a confirmation email.
12. **The new booking** is also visible on `/bookings/` (My Bookings) and on the operations dashboard if the customer is staff.

---

## 3.3 Shorter flows

### 3.3.1 Sign up
```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor G as Guest
    participant V as SignUpView
    participant F as SignUpForm
    participant U as User (DB)
    G->>V: GET /accounts/signup/
    V-->>G: Render wizard form
    G->>V: POST form
    V->>F: Validate
    F-->>V: cleaned_data
    V->>U: create_user + save
    V->>V: login(user)
    V-->>G: Redirect to /accounts/dashboard/
```

### 3.3.2 Cancel booking
```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor C as Customer
    participant V as Cancel View
    participant B as Booking (DB)
    participant Pay as Payment (DB)
    participant TS as TimeSlot (DB)
    C->>V: GET /bookings/<id>/cancel/  (confirm page)
    V-->>C: Render confirm
    C->>V: POST confirm
    V->>B: is_cancellable?
    alt Yes
        V->>B: status='cancelled'
        opt payment exists and paid
            V->>Pay: status='refunded'
        end
        V->>TS: update_status
        V-->>C: Redirect to /bookings/  (success toast)
    else No
        V-->>C: Redirect to /bookings/<id>/  (error toast)
    end
```

### 3.3.3 Reschedule booking
```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor C as Customer
    participant V as Reschedule View
    participant TS as TimeSlot (DB)
    participant B as Booking (DB)
    C->>V: GET /bookings/<id>/reschedule/
    V->>TS: List future open slots (any drop zone)
    V-->>C: Render radio list
    C->>V: POST new_slot
    V->>TS: is_available?
    alt Yes
        V->>B: time_slot = new_slot
        V->>TS: update_status (old + new slot)
        V-->>C: Redirect to /bookings/<id>/
    else No
        V-->>C: Render form with error
    end
```

### 3.3.4 Admin slot calendar — one-click cancel (weather)
```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor A as Admin
    participant V as Slots Calendar
    participant AV as Slot Action view
    participant TS as TimeSlot (DB)
    A->>V: GET /manage/slots/
    V->>TS: list slots grouped by date
    TS-->>V: slots
    V-->>A: Render rows with status pills
    A->>AV: POST /manage/slots/<id>/action/  action=cancel
    AV->>TS: UPDATE status='cancelled'
    AV-->>A: Redirect back to /manage/slots/ (warning toast)
```

### 3.3.5 Admin creates a new slot
```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor A as Admin
    participant V as Slot Create view
    participant DZ as DropZone (DB)
    participant TS as TimeSlot (DB)
    A->>V: GET /manage/slots/new/
    V->>DZ: list zones
    V-->>A: Render form
    A->>V: POST {drop_zone, date, start_time, capacity}
    V->>TS: get_or_create(slot)
    alt New slot
        V-->>A: Redirect to /manage/slots/ (success toast)
    else Slot already exists
        V-->>A: Redirect to /manage/slots/ (info toast, no duplicate)
    end
```

---

## 3.4 Why this design

- **Eligibility lives in the form** (`BookingDetailsForm.clean()`) so error messages are user-friendly and grouped.
- **Capacity is re-checked at step-4 entry and at save time**, so two concurrent users can't both grab the last seat(s).
- **State via URL query params** (`?dropzone=X&package=Y&slot=Z`) keeps the wizard stateless — refreshing a step doesn't lose progress, and the URL can be shared.
- **Payment is a separate view** so the booking can be created in `pending` state, which mirrors real-world flows.
- **Confirmation page replaces an email** to keep the assignment self-contained.
- **`TimeSlot.update_status()` is called at every booking/cancel/reschedule** so the slot's `status` stays in sync with `booked_count` without polling.
