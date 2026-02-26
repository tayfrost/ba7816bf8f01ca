# SentinelAI – Front-End Styling & UI System

This repository contains the front-end architecture for **SentinelAI**, a burnout-monitoring platform. This documentation covers the static UI elements, branding, and component-based design system.

---

## Branding & Visual Identity

The design system is built on a high-contrast, "Glassmorphic-Glow" aesthetic that hopes to enhance user experience and mirrors the sentiment of warmth and wellbeing.

### Color Palette
The primary theme is defined via Tailwind CSS variables to ensure consistency across all components:

* **Primary Gradient:** A vertical transition from **Rich Golden Orange** (`#e38d26`) to **Warm Oatmeal** (`#f7e9c1`).
* **Brand Deep:** A professional **Deep Purple** (`#3f0345`) used for primary text, super-cards, and high-contrast UI containers.
* **Brand Accent:** A **Bright Golden Halo** (`#fcd34d`) used for interactive highlights and status indicators.

### Typography & Base Styles
The application uses a sans-serif stack for readability, with high-weight serif headings for the landing and onboarding pages to provide a premium, editorial feel.

### Logo Symbolism: The Sentinel Halo
The brand's visual anchor is the **Glowing Angel Halo**, which serves as a metaphor for the nature of our platform, a "guardian" presence that watches over employee wellbeing.

---

## Static & Styling Elements

The UI is built using a **Component-Based Architecture**, focusing on reusability and glassmorphism effects.

### Layout Components
* *Super Cards:** Utilizes `backdrop-blur-3xl` and `white/10` opacity layers to create depth against the brand gradient.
* **Bento-Box Dashboard:** A grid-based layout for the `Dashboard` overview that organizes metrics into distinct, scannable widgets.
* **Glowing Data Viz Shells:** Pre-styled containers designed specifically to house glowing SVG line charts, using `brand-deep` backgrounds to make neon signals pop.

---

## Technical Implementation (Styling)

The project leverages **Tailwind CSS v4** with a custom theme configuration:

```css
@theme {
  --color-top: #e38d26;
  --color-bottom: #f7e9c1;
  --color-brand-deep: #3f0345;
  --color-brand-accent: #fcd34d;
}