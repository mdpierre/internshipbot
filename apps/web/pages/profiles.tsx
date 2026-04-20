import { ChangeEvent, useEffect, useMemo, useState } from "react";

type Experience = {
  employer: string;
  title: string;
  start_date: string;
  end_date: string;
  location: string;
  description: string;
};

type Education = {
  school: string;
  degree: string;
  major: string;
  graduation_year: string;
  gpa: string;
};

type Profile = {
  slot: string;
  display_name: string;
  profile_name: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  linkedin: string;
  website: string;
  github: string;
  target_title: string;
  target_salary: string;
  work_authorization: string;
  require_sponsorship: string;
  veteran: string;
  disability: string;
  gender: string;
  ethnicity: string;
  summary: string;
  resume_label: string;
  resume_filename: string | null;
  resume_content_type: string | null;
  resume_uploaded_at: string | null;
  is_active: boolean;
  experiences: Experience[];
  educations: Education[];
};

type ExtensionConfig = {
  active_profile_slot: string;
  dashboard_url: string;
  healthy: boolean;
};

const emptyExperience = (): Experience => ({
  employer: "",
  title: "",
  start_date: "",
  end_date: "",
  location: "",
  description: "",
});

const emptyEducation = (): Education => ({
  school: "",
  degree: "",
  major: "",
  graduation_year: "",
  gpa: "",
});

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedSlot, setSelectedSlot] = useState("profile_1");
  const [form, setForm] = useState<Profile | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [extensionConfig, setExtensionConfig] = useState<ExtensionConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [profilesRes, configRes] = await Promise.all([
        fetch("/api/profiles"),
        fetch("/api/extension/config"),
      ]);
      const profilesJson = await profilesRes.json();
      const configJson = await configRes.json();
      const loadedProfiles: Profile[] = profilesJson.data ?? [];
      setProfiles(loadedProfiles);
      setSelectedSlot(configJson.active_profile_slot ?? loadedProfiles[0]?.slot ?? "profile_1");
      setExtensionConfig(configJson);
      setLoading(false);
    }
    load().catch(() => {
      setStatus("Could not load profile data. Is the API running?");
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    const profile = profiles.find((item) => item.slot === selectedSlot);
    setForm(profile ? JSON.parse(JSON.stringify(profile)) : null);
  }, [profiles, selectedSlot]);

  const selectedProfile = useMemo(
    () => profiles.find((item) => item.slot === selectedSlot) ?? null,
    [profiles, selectedSlot]
  );

  function setField<K extends keyof Profile>(key: K, value: Profile[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function setExperience(index: number, key: keyof Experience, value: string) {
    setForm((prev) => {
      if (!prev) return prev;
      const experiences = [...prev.experiences];
      experiences[index] = { ...experiences[index], [key]: value };
      return { ...prev, experiences };
    });
  }

  function setEducation(index: number, key: keyof Education, value: string) {
    setForm((prev) => {
      if (!prev) return prev;
      const educations = [...prev.educations];
      educations[index] = { ...educations[index], [key]: value };
      return { ...prev, educations };
    });
  }

  async function refreshProfiles(preferredSlot = selectedSlot) {
    const res = await fetch("/api/profiles");
    const json = await res.json();
    const loadedProfiles: Profile[] = json.data ?? [];
    setProfiles(loadedProfiles);
    setSelectedSlot(preferredSlot);

    const configRes = await fetch("/api/extension/config");
    setExtensionConfig(await configRes.json());
  }

  async function handleSave(markActive = false) {
    if (!form) return;
    setStatus("Saving profile...");
    const payload = {
      ...form,
      is_active: markActive ? true : form.is_active,
      experiences: form.experiences.length ? form.experiences : [emptyExperience()],
      educations: form.educations.length ? form.educations : [emptyEducation()],
    };
    const res = await fetch(`/api/profiles/${form.slot}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      setStatus("Could not save profile.");
      return;
    }
    await refreshProfiles(form.slot);
    setStatus(markActive ? "Saved and set as active." : "Profile saved.");
  }

  async function handleUploadResume(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !form) return;
    setStatus("Uploading resume...");
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`/api/profiles/${form.slot}/resume`, {
      method: "POST",
      body,
    });
    if (!res.ok) {
      setStatus("Resume upload failed.");
      return;
    }
    await refreshProfiles(form.slot);
    setStatus("Resume uploaded.");
    event.target.value = "";
  }

  async function handleParseResume() {
    if (!form) return;
    setStatus("Parsing resume...");
    const res = await fetch(`/api/profiles/${form.slot}/parse-resume`, {
      method: "POST",
    });
    const json = await res.json();
    if (!res.ok || !json.data) {
      setStatus(json.detail ?? "Resume parsing failed.");
      return;
    }
    setForm((prev) => (prev ? { ...prev, ...json.data.parsed_profile, slot: prev.slot } : prev));
    setStatus("Parsed resume into the form. Review and save when ready.");
  }

  if (loading) {
    return <p style={{ color: "var(--text-muted)" }}>Loading profiles…</p>;
  }

  return (
    <div className="stack-lg">
      <div className="card card--immersive">
        <div className="card__header">
          <div>
            <span className="card__title">Desktop Onboarding</span>
            <h2 style={{ marginTop: "0.4rem" }}>Profiles and extension pairing</h2>
          </div>
        </div>
        <p style={{ color: "var(--text-muted)", maxWidth: 760 }}>
          The desktop app is the source of truth now. Edit your three profile slots here,
          upload and parse resumes locally, and let the Chrome extension pull the active slot
          from the local backend when you autofill applications.
        </p>
        <div className="info-grid" style={{ marginTop: "1rem" }}>
          <div className="info-card">
            <span className="section-label">Extension</span>
            <p>{extensionConfig?.healthy ? "Connected to local backend" : "Waiting for backend"}</p>
          </div>
          <div className="info-card">
            <span className="section-label">Active Slot</span>
            <p>{extensionConfig?.active_profile_slot ?? "profile_1"}</p>
          </div>
          <div className="info-card">
            <span className="section-label">Workflow</span>
            <p>Upload resume, review parsed data, save, then autofill from the extension.</p>
          </div>
        </div>
      </div>

      <div className="profiles-layout">
        <div className="card card--immersive">
          <div className="card__header">
            <span className="card__title">Profile Slots</span>
          </div>
          <div className="stack-md">
            {profiles.map((profile) => (
              <button
                key={profile.slot}
                className={`profile-slot${profile.slot === selectedSlot ? " profile-slot--active" : ""}`}
                onClick={() => setSelectedSlot(profile.slot)}
              >
                <div>
                  <strong>{profile.display_name}</strong>
                  <p style={{ color: "var(--text-muted)", marginTop: "0.25rem" }}>
                    {profile.profile_name || "Empty profile"}
                  </p>
                </div>
                <span className={`badge ${profile.is_active ? "badge-greenhouse" : "badge-manual"}`}>
                  {profile.is_active ? "Active" : "Inactive"}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="card card--immersive">
          {!form || !selectedProfile ? (
            <p style={{ color: "var(--text-muted)" }}>Select a profile slot to begin.</p>
          ) : (
            <div className="stack-lg">
              <div className="card__header">
                <div>
                  <span className="card__title">Editing</span>
                  <h2 style={{ marginTop: "0.4rem" }}>{selectedProfile.display_name}</h2>
                </div>
                <div className="drawer__actions" style={{ marginTop: 0 }}>
                  <button className="btn btn-ghost" onClick={() => handleSave(true)}>
                    Make Active
                  </button>
                  <button className="btn btn-primary" onClick={() => handleSave(false)}>
                    Save
                  </button>
                </div>
              </div>

              <div className="form-grid">
                <label className="form-field">
                  <span>Display Name</span>
                  <input value={form.display_name} onChange={(e) => setField("display_name", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Profile Name</span>
                  <input value={form.profile_name} onChange={(e) => setField("profile_name", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>First Name</span>
                  <input value={form.first_name} onChange={(e) => setField("first_name", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Last Name</span>
                  <input value={form.last_name} onChange={(e) => setField("last_name", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Email</span>
                  <input value={form.email} onChange={(e) => setField("email", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Phone</span>
                  <input value={form.phone} onChange={(e) => setField("phone", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>City</span>
                  <input value={form.city} onChange={(e) => setField("city", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>State</span>
                  <input value={form.state} onChange={(e) => setField("state", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>ZIP</span>
                  <input value={form.zip} onChange={(e) => setField("zip", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Country</span>
                  <input value={form.country} onChange={(e) => setField("country", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>LinkedIn</span>
                  <input value={form.linkedin} onChange={(e) => setField("linkedin", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>GitHub</span>
                  <input value={form.github} onChange={(e) => setField("github", e.target.value)} />
                </label>
                <label className="form-field form-field--full">
                  <span>Website</span>
                  <input value={form.website} onChange={(e) => setField("website", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Target Title</span>
                  <input value={form.target_title} onChange={(e) => setField("target_title", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Target Salary</span>
                  <input value={form.target_salary} onChange={(e) => setField("target_salary", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Work Authorization</span>
                  <input value={form.work_authorization} onChange={(e) => setField("work_authorization", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Require Sponsorship</span>
                  <input value={form.require_sponsorship} onChange={(e) => setField("require_sponsorship", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Veteran</span>
                  <input value={form.veteran} onChange={(e) => setField("veteran", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Disability</span>
                  <input value={form.disability} onChange={(e) => setField("disability", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Gender</span>
                  <input value={form.gender} onChange={(e) => setField("gender", e.target.value)} />
                </label>
                <label className="form-field">
                  <span>Ethnicity</span>
                  <input value={form.ethnicity} onChange={(e) => setField("ethnicity", e.target.value)} />
                </label>
                <label className="form-field form-field--full">
                  <span>Summary</span>
                  <textarea
                    className="url-textarea"
                    rows={4}
                    value={form.summary}
                    onChange={(e) => setField("summary", e.target.value)}
                  />
                </label>
              </div>

              <div className="stack-md">
                <div className="card__header">
                  <span className="card__title">Resume</span>
                </div>
                <div className="drawer__actions" style={{ marginTop: 0 }}>
                  <label className="btn btn-ghost">
                    Upload Resume
                    <input type="file" accept=".pdf" hidden onChange={handleUploadResume} />
                  </label>
                  <button className="btn btn-primary" onClick={handleParseResume}>
                    Parse Uploaded Resume
                  </button>
                </div>
                <p style={{ color: "var(--text-muted)" }}>
                  {selectedProfile.resume_label
                    ? `Current file: ${selectedProfile.resume_label}`
                    : "No resume uploaded yet."}
                </p>
              </div>

              <div className="stack-md">
                <div className="card__header">
                  <span className="card__title">Experience</span>
                </div>
                {form.experiences.map((experience, index) => (
                  <div key={index} className="subcard">
                    <div className="form-grid">
                      <label className="form-field">
                        <span>Employer</span>
                        <input value={experience.employer} onChange={(e) => setExperience(index, "employer", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Title</span>
                        <input value={experience.title} onChange={(e) => setExperience(index, "title", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Start Date</span>
                        <input value={experience.start_date} onChange={(e) => setExperience(index, "start_date", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>End Date</span>
                        <input value={experience.end_date} onChange={(e) => setExperience(index, "end_date", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Location</span>
                        <input value={experience.location} onChange={(e) => setExperience(index, "location", e.target.value)} />
                      </label>
                      <label className="form-field form-field--full">
                        <span>Description</span>
                        <textarea
                          className="url-textarea"
                          rows={3}
                          value={experience.description}
                          onChange={(e) => setExperience(index, "description", e.target.value)}
                        />
                      </label>
                    </div>
                  </div>
                ))}
              </div>

              <div className="stack-md">
                <div className="card__header">
                  <span className="card__title">Education</span>
                </div>
                {form.educations.map((education, index) => (
                  <div key={index} className="subcard">
                    <div className="form-grid">
                      <label className="form-field">
                        <span>School</span>
                        <input value={education.school} onChange={(e) => setEducation(index, "school", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Degree</span>
                        <input value={education.degree} onChange={(e) => setEducation(index, "degree", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Major</span>
                        <input value={education.major} onChange={(e) => setEducation(index, "major", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>Graduation Year</span>
                        <input value={education.graduation_year} onChange={(e) => setEducation(index, "graduation_year", e.target.value)} />
                      </label>
                      <label className="form-field">
                        <span>GPA</span>
                        <input value={education.gpa} onChange={(e) => setEducation(index, "gpa", e.target.value)} />
                      </label>
                    </div>
                  </div>
                ))}
              </div>

              {status && <p style={{ color: "var(--text-muted)" }}>{status}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
