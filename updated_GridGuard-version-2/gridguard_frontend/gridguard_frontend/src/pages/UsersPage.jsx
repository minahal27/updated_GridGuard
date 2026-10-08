import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Banner, GridPulse } from "../components/Common";

export default function UsersPage() {
  const [users, setUsers] = useState([]), [error, setError] = useState(""), [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "analyst" });
  const load = () => { setLoading(true); api.listUsers().then(setUsers).catch(e => setError(e.message)).finally(() => setLoading(false)); };
  useEffect(load, []);
  const create = async e => { e.preventDefault(); setError(""); try { await api.register(form); setForm({ name: "", email: "", password: "", role: "analyst" }); load(); } catch (err) { setError(err.message); } };
  return <div className="flex-col gap-5"><div><h2>User administration</h2><p className="mt-2">Create analyst and administrator accounts with controlled access.</p></div>{error && <Banner type="error">{error}</Banner>}<form className="panel panel-pad flex items-end gap-3" style={{ flexWrap: "wrap" }} onSubmit={create}>{[["name","Name","text"],["email","Email","email"],["password","Temporary password","password"]].map(([key,label,type])=><div className="field" key={key}><label>{label}</label><input required minLength={key === "password" ? 8 : undefined} className="input" type={type} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></div>)}<div className="field"><label>Role</label><select className="select" value={form.role} onChange={e=>setForm({...form,role:e.target.value})}><option value="analyst">Analyst</option><option value="admin">Administrator</option></select></div><button className="btn btn-primary">Create user</button></form><div className="panel">{loading?<GridPulse label="Loading users"/>:<div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.role}</td><td>{u.status}</td></tr>)}</tbody></table></div>}</div></div>;
}
