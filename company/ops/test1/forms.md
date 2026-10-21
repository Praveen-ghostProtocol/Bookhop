# Test 1 — Forms, verbatim and paste-ready

Two forms. Both are built in Google Forms. Nothing else is collected anywhere.

**Build rules for whoever creates these in Google Forms**

1. Paste the text exactly. Do not improve the wording. The words were chosen
   against legal constraints (see §8 of `../TEST-1-CONCIERGE-PILOT.md`).
2. Turn OFF "Collect email addresses" in Google Forms settings. We collect a
   campus roll number and a phone number ourselves, in the form, so that we
   know exactly what we hold.
3. Turn OFF file/photo upload. A photo would require Google sign-in and pulls
   in a Google account identifier we do not need.
4. Every question marked **[required]** is required. The rest are optional.
5. Never add a question asking what price was actually paid. See §8.
6. Response destination: one Google Sheet per form. The operator copies into
   the tracking sheet; the Forms sheets are the raw record and are never edited.
7. **Never publish, share or display the responses.** No summary chart, no
   "see all responses" link, no printed list of available books. Turn OFF
   "See summary charts and text responses" in Google Forms. The operator holds
   the list and nobody else sees it, ever. A browsable list of books on offer
   would make BookHop an e-commerce entity, and Rule 4(1)(a) then requires an
   incorporated company that does not yet exist.
8. **Collect none of these, anywhere, in any question**: date of birth, PAN,
   Aadhaar or any government ID, UPI handle or payment identifier, postal
   address, and what price was actually paid.

---

# FORM A — BookHop pilot: list a book or ask for one

**Form title**

```
BookHop campus pilot — list a book, or ask for one
```

**Form description**

```
This is a two-week pilot run by hand. There is no app. A person reads this
form and tries to put you in touch with someone on this campus who has the
book you need, or who needs the book you have.

It takes about 90 seconds. You can stop at any time.

What we do with what you write: we use it to make a match and to count how
well the pilot worked. We keep it until 31 January 2027 and then delete it.
We do not sell it, we do not pass it to anyone outside the pilot, and we do
not publish it. Nobody can browse what anyone else has listed - there is no
list to look at, only a person who reads the responses and tries to make a
match. If you are matched with someone, we will share your first name and
your phone number with that one person so you can arrange to meet, and
nothing else.

Half the matches in this pilot, picked at random by a sealed envelope before
anyone signed up, are asked to pay a 6% pilot fee in cash between the two
students. The other half are asked for nothing. Which half you land in is
decided by the envelope and by nothing whatsoever about you. That is the
experiment. You are free to say no to the fee and nothing happens if you do.

To take part you must be 18 or over. We do not ask your date of birth and we
do not ask for any ID - we ask you to tell us, and the person running the
pilot will ask you again in person.

BookHop does not check, grade, inspect or stand behind any book. Everything
said about a book is said by the student who owns it. You look at the book
yourself before you pay anything. Money, if any, is between you and the other
student. BookHop never handles it.

Questions, or want your details deleted: message the pilot number on the
poster. Deletion takes one working day.
```

### Section 1 — You

**Q1. What do you want to do today?** [required] · multiple choice
```
I have a book to pass on
I am looking for a book
Both
```

**Q2. Your first name and the first letter of your surname** [required] · short answer
```
Example: Priya R
```

**Q3. Your college roll number** [required] · short answer
```
We use this to check you study here. We do not check it against any
government ID and we never ask for Aadhaar or PAN.
```

**Q4. Mobile number (WhatsApp)** [required] · short answer
```
We will message you from the pilot number. If you are matched, this number is
shared with that one person only.
```

**Q5. Are you 18 or over today?** [required] · multiple choice
```
Yes
No
```
*Help text under Q5:*
```
We do not ask your date of birth and we do not want any ID. We are asking you
to tell us. The person running the pilot will also ask you in person before
matching you. If you are under 18 we will not match you and we will delete
what you entered the same day - nothing is kept.
```

**Q6. Department and year** [required] · short answer

### Section 2 — The book
*(Google Forms: show this section only if Q1 is not "I am looking for a book".
If branching is awkward, leave it visible and mark the section "Skip if you
are only looking for a book.")*

**Q7. Title** [required] · short answer

**Q8. Author** · short answer

**Q9. Publisher** · short answer

**Q10. Edition and year printed** [required] · short answer
```
Look at the title page or the back of the title page. "4th edition, 2022".
If you cannot find it, write "not stated". Editions matter more than anything
else on this form.
```

**Q11. ISBN** · short answer
```
13 digits, usually above the barcode. Optional.
```

**Q12. Course code this book is prescribed for** · short answer
```
Example: MA3251. Leave blank if you do not know.
```

**Q13. Condition, in your own judgement** [required] · multiple choice
```
LIKE NEW - barely opened, no marks
GOOD - some marks or notes, spine and all pages intact
FAIR - heavy notes, highlighting, worn cover, all pages intact
POOR - pages loose or missing, water damage, cover detached
```
*Help text under Q13:*
```
This is your description, not ours. BookHop does not inspect books and does
not confirm what you have written here. The person who comes to meet you will
look at the book themselves.
```

**Q14. Asking price in rupees** [required] · short answer
```
What you are asking for. Not a final price - you two settle that between
yourselves when you meet. Write 0 if you are giving it away.
```

### Section 3 — The book you want
*(Show only if Q1 is "I am looking for a book" or "Both".)*

**Q15. Title you need** [required] · short answer

**Q16. Edition / year you need, if your syllabus names one** · short answer

**Q17. Course code** · short answer

**Q18. Highest you would go, in rupees** · short answer
```
Optional. It helps us not waste your time on a match you would refuse.
```

### Section 4 — Meeting and consent

**Q19. When are you usually on campus and free for ten minutes?** [required] · checkboxes
```
Weekday 09:00-11:00
Weekday 11:00-13:00
Weekday 13:00-15:00
Weekday 15:00-18:00
Weekend
```

**Q20.** [required] · checkboxes — all four must be ticked
```
I am 18 or over.
I agree that BookHop can keep what I have written here until 31 January 2027
to run this pilot and count the results, and can share my first name and
phone number with one person I am matched with.
I understand that BookHop does not check or stand behind any book or any
person, does not handle any money, and that meetings happen at the listed
campus points, in daylight, and are my own decision.
I understand that this is an experiment in which different participants are
treated differently on price: half the matches, picked at random before
anyone signed up, are asked for a 6% pilot fee paid in cash between the two
students, and half are asked for nothing. Which half I am in is decided at
random and not by anything about me. I can decline the fee and nothing
happens if I do.
```

**Q21. Anything else?** · paragraph

**Confirmation message shown after submitting**
```
Got it. If we find you a match we will message you from the pilot number
within a day or two. If we cannot, we will tell you that too.

Meetings happen only at the three campus points listed on the poster, between
09:00 and 18:00. Look at the book before any money moves.
```

---

# FORM B — BookHop pilot: what happened at the handover

One submission per person per match. The buyer fills it in. The seller fills
it in. Separately. Neither sees the other's answers.

**Form title**

```
BookHop pilot - what happened
```

**Form description**

```
Thirty seconds. Fill this in right after you meet, while you are still
standing there if you can.

Answer it even if nothing happened, even if the other person did not turn up,
and even if you sorted it out between yourselves without us. Especially then.
We are measuring what people actually do, and a blank is worse for us than
any answer you can give.

We do not ask what price you paid and we do not want to know.
```

**Q1. Match code** [required] · short answer
```
The code on the card we gave you. Looks like M-014.
```

**Q2. Which were you?** [required] · multiple choice
```
I had the book
I wanted the book
```

**Q3. Your first name and the first letter of your surname** [required] · short answer

**Q4. Did the book change hands?** [required] · multiple choice
```
Yes
No
Not yet, but we have agreed to meet again
```

**Q5. When?** · date and time
*(Show if Q4 = Yes.)*

**Q6. Where did you meet?** [required] · multiple choice
```
Point 1 - canteen courtyard
Point 2 - library steps
Point 3 - main gate notice board
Somewhere else on campus
We did not meet
```

**Q7. Were you told that a 6% pilot fee applies to this match?** [required] · multiple choice
```
Yes
No
I do not remember
```

**Q8. Did that fee get paid, in cash?** [required] · multiple choice
```
Yes, in cash
No
No fee applied to my match
```
*Help text under Q8:*
```
Either answer is completely fine and nothing happens either way. We are
asking the other person the same question separately. An honest "no" is more
use to us than a polite "yes".
```

*(Form B has no Q9. An earlier draft asked for the last four digits of a UPI
reference so that the buyer's and the seller's answers could be checked
against each other. The fee is cash and we collect no payment identifier of
any kind, so that check does not exist. See §2.3 and §2.4 of the kit for what
that costs the measurement.)*

**Q10. Was the book as the other person described it?** [required] · multiple choice
```
Yes
Mostly - minor differences
No - clearly different from the description
I did not look closely
Did not apply
```

**Q11. Did you look at the book before any money moved?** [required] · multiple choice
```
Yes
No
No money moved
```

**Q12. Did anything go wrong, or feel uncomfortable?** · paragraph
```
Lateness, a no-show, an argument, anything at all. If something happened that
worried you, write it here or message the pilot number.
```

**Q13. If you two deal again, would you go through BookHop or just message each
other directly?** [required] · multiple choice
```
Through BookHop
Message each other directly
Would not deal again
Not sure
```

**Confirmation message shown after submitting**
```
Thanks. That is the whole pilot - a form, a spreadsheet and one person. If
anything about the meeting worried you, message the pilot number now.
```

---

## What is deliberately not asked, and why

| Not asked | Why |
|---|---|
| What price was actually paid | A recorded settled consideration creates a determinable "gross amount" under the s194-O Explanation. The listing carries an **asking price** only. See `evidence/COMPLIANCE.md` §4.3 and blocker P14. |
| PAN, Aadhaar, any government ID | P14 and DPDP §1.4. Collecting a financial identifier would also pull the pilot into the SPDI regime it currently sits outside. |
| Date of birth | Compliance envelope for Test 1. The 18+ gate is a declaration plus an in-person check by the operator, logged in the sheet. See §8 of the kit for what that gate can and cannot do. |
| UPI handle, UPI reference, or any payment identifier | Compliance envelope for Test 1. The fee is cash. This removes the only objective cross-check on fee-paid; §2.3 and §2.4 of the kit state the consequence rather than papering over it. |
| Photo of the book | Would force a Google sign-in and bring in an account identifier we do not need. The buyer inspects the physical book instead, which is the actual remedy. |
| Home address | Never collected, never published. Handovers are at three named campus points. |
| Gender, caste, income, anything about a third party | Not needed to answer any of the five questions this pilot exists to answer. |
| "Did you feel safe?" | We do not use the word. See §8 of the kit. Q12 asks the same thing in words that do not imply BookHop provides safety. |
