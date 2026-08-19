import {
  Children,
  cloneElement,
  isValidElement,
  type CSSProperties,
  type ReactElement,
  type ReactNode,
} from "react";

interface CardGridProps {
  /** Minimum width of each card before wrapping, e.g. "150px". */
  minWidth: string;
  gap?: string;
  style?: CSSProperties;
  children: ReactNode;
}

/**
 * Row of cards that wraps without ever leaving dead space in a partially
 * filled last row. `grid-template-columns: repeat(auto-fit, minmax(...))`
 * looks like it should handle this, but grid column tracks are shared
 * across every row - auto-fit only collapses tracks that are empty in
 * ALL rows. When the item count doesn't divide evenly into a row (e.g. 4
 * cards where 3 fit per row), the leftover row's unused cells stay part
 * of the grid and render as blank space. Flexbox has no such shared-track
 * concept: each wrapped line distributes its own free space among
 * whichever items actually landed in it.
 */
export function CardGrid({
  minWidth,
  gap = "12px",
  style,
  children,
}: CardGridProps) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap, ...style }}>
      {Children.map(children, (child) => {
        if (!isValidElement(child)) return child;
        const el = child as ReactElement<{ style?: CSSProperties }>;
        return cloneElement(el, {
          style: {
            flex: `1 1 ${minWidth}`,
            minWidth: 0,
            ...(el.props.style || {}),
          },
        });
      })}
    </div>
  );
}
