---
name: Heritage Tech
colors:
  surface: '#fbf8fc'
  surface-dim: '#dbd9dc'
  surface-bright: '#fbf8fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f6'
  surface-container: '#efedf0'
  surface-container-high: '#e9e7eb'
  surface-container-highest: '#e4e2e5'
  on-surface: '#1b1b1e'
  on-surface-variant: '#44474e'
  inverse-surface: '#303033'
  inverse-on-surface: '#f2f0f3'
  outline: '#75777e'
  outline-variant: '#c5c6cf'
  surface-tint: '#4e5e80'
  primary: '#031634'
  on-primary: '#ffffff'
  primary-container: '#1a2b4a'
  on-primary-container: '#8293b7'
  inverse-primary: '#b6c6ee'
  secondary: '#745b1b'
  on-secondary: '#ffffff'
  secondary-container: '#ffdc8e'
  on-secondary-container: '#795f1f'
  tertiary: '#221400'
  on-tertiary: '#ffffff'
  tertiary-container: '#3d2700'
  on-tertiary-container: '#af8d5b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#b6c6ee'
  on-primary-fixed: '#081b39'
  on-primary-fixed-variant: '#364767'
  secondary-fixed: '#ffdf9b'
  secondary-fixed-dim: '#e4c278'
  on-secondary-fixed: '#251a00'
  on-secondary-fixed-variant: '#5a4302'
  tertiary-fixed: '#ffddaf'
  tertiary-fixed-dim: '#e7c18a'
  on-tertiary-fixed: '#281800'
  on-tertiary-fixed-variant: '#5c4217'
  background: '#fbf8fc'
  on-background: '#1b1b1e'
  surface-variant: '#e4e2e5'
typography:
  h1:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: '0'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

The design system is rooted in the "German Mittelstand" philosophy—a synthesis of century-old reliability and modern operational efficiency. The visual language conveys stability, precision, and high-trust professionalism. 

The aesthetic style is **Corporate / Modern**, leaning heavily into high-end B2B standards. It utilizes a structured hierarchy to handle complex property data while maintaining a "premium" feel through intentional whitespace and a restrained use of the gold accent. The interface should feel like a digital extension of a physical, prestigious office: organized, quiet, and authoritative.

## Colors

This design system uses a palette that balances authority with warmth. **Rahlfs Navy** is the foundation, used for headers, primary actions, and brand identification. **Muted Gold** is reserved for high-value highlights, such as premium features or specific call-to-actions, ensuring it retains its impact without appearing gaudy.

For the mobile experience, the color logic follows a native chat pattern: the header retains the Navy identity, while the message thread utilizes soft grays and crisp whites to ensure readability. The desktop "Cockpit" supports a true Dark Mode, swapping the light neutral backgrounds for deep navy and slate tones to reduce eye strain during long-form data management.

## Typography

The typography system relies exclusively on **Inter** to provide a systematic, utilitarian clarity essential for property management. All text must follow **sentence case** to maintain a professional yet conversational tone, avoiding the aggression of all-caps styling.

Hierarchy is established through weight and scale rather than decorative flourishes. Headlines are set with tighter letter spacing and heavier weights for a grounded look, while body text uses generous line heights to ensure that dense reports and chat logs remain legible and easy to scan.

## Layout & Spacing

The layout philosophy differs by platform but maintains a shared rhythm based on an **8px grid**. 

- **Mobile:** Uses a fluid layout with safe-area margins (16px). Message bubbles are grouped with 4px spacing, while distinct user turns are separated by 12px to 16px.
- **Desktop (Cockpit):** Employs a **fixed grid** system for the main dashboard to ensure data tables and widgets remain predictable. A 12-column grid with 24px gutters is standard. 

Generous whitespace (the "lg" and "xl" units) is used to separate high-level sections, preventing the data-heavy environment from feeling cluttered or overwhelming.

## Elevation & Depth

Visual hierarchy in this design system is achieved through **tonal layers** and **low-contrast outlines**. 

On the Desktop Cockpit, cards and widgets use a subtle 1px border (`#e2e8f0` in light mode) rather than heavy shadows to maintain a clean, flat B2B aesthetic. Elevation is reserved for floating elements like modals or dropdown menus, which utilize **ambient shadows**—diffused, low-opacity (10-15%) blurs that give the impression of the element sitting just above the surface.

In the Mobile Chat, depth is created through color-coding: user bubbles are solid Navy, while bot bubbles are a flat Light Gray, creating a clear "layered" conversation flow without the need for physical shadows.

## Shapes

The shape language is consistently **Rounded**, striking a balance between the friendliness of a modern chat app and the structure of a corporate dashboard. 

Standard components like buttons, input fields, and chat bubbles use a `0.5rem` radius. Larger containers, such as dashboard cards or the main chat window container, use `1rem` (rounded-lg) to soften the interface and reinforce the premium, polished feel of the brand. Avatars, specifically the bot's "R" monogram, are always perfectly circular.

## Components

### Buttons
- **Primary:** Solid Rahlfs Navy with white text. Rounded (0.5rem).
- **Secondary/Action:** Muted Gold background with Navy text, used sparingly for "Premium" actions or conversion points.
- **Ghost:** Navy outline with no fill, used for secondary dashboard actions.

### Chat Bubbles
- **User (Right):** Rahlfs Navy background, white text. Rounded-lg corners, with the bottom-right corner sharpened to indicate direction.
- **Bot (Left):** White or very light gray background, Navy text. Rounded-lg corners, with the bottom-left corner sharpened.
- **Bot Avatar:** A Navy circle containing the "R" monogram in white or gold.

### Cockpit Widgets (Dashboard)
- White background containers with a subtle gray border.
- Header area within the card uses `label-sm` for categories.
- Data points are emphasized using Rahlfs Navy in `h3` or `h2` sizes.

### Input Fields
- Clean, 1px bordered boxes. 
- Active state is indicated by a 2px Rahlfs Navy border, never a glow.
- Labels are always positioned above the field in `label-md`.

### Feedback & Status
- **Emergencies/Overdue:** Soft Red text or small circular badges.
- **In-Progress:** Amber/Gold status chips.
- **Completed:** Rahlfs Navy or muted green accents.