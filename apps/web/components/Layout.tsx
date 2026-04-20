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
    { href: "/profiles", label: "Profiles" },
    { href: "/jobs", label: "Jobs" },
    { href: "/sessions", label: "Sessions" },
    { href: "/runs", label: "Runs" },
  ];

  return (
    <div className="app-frame">
      <div className="topline">
        <span>local control surface</span>
        <span>http://127.0.0.1:8000</span>
        <span>desktop-assisted apply mode</span>
      </div>

      <div className="workspace-shell">
        <header className="workspace-header">
          <div className="brand-lockup">
            <div className="brand-mark" />
            <div>
              <p className="brand-kicker">Operations</p>
              <h1>applybot</h1>
            </div>
          </div>

          <nav className="workspace-nav">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`workspace-nav__item${
                router.pathname === item.href ? " workspace-nav__item--active" : ""
              }`}
            >
              {item.label}
            </Link>
          ))}
          </nav>

          <div className="workspace-account">
            <span className="status-pill">Green energy</span>
            <span>Marlene Nowak</span>
          </div>
        </header>

        <main>{children}</main>
      </div>
    </div>
  );
}
