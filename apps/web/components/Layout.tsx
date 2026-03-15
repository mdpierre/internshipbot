import Link from "next/link";
import { useRouter } from "next/router";
import { ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export default function Layout({ children }: Props) {
  const router = useRouter();

  const navItems = [
    { href: "/", label: "Home" },
    { href: "/jobs", label: "Jobs" },
    { href: "/runs", label: "Runs" },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem 1.5rem" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "2rem",
          marginBottom: "2rem",
          paddingBottom: "1rem",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>applybot</h1>
        <nav style={{ display: "flex", gap: "1.25rem" }}>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{
                color:
                  router.pathname === item.href
                    ? "var(--accent)"
                    : "var(--text-muted)",
                fontWeight: router.pathname === item.href ? 600 : 400,
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main>{children}</main>
    </div>
  );
}
