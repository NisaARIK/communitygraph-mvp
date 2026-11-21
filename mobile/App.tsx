import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { supabase } from './src/supabase';
import Projects from './src/Projects';
import AIAnalysis from './src/AIAnalysis';

type Profile = {
  full_name: string | null;
  role: string | null;
  bio: string | null;
  industry: string | null;
  startup_name?: string | null;
  hub_name?: string | null;
  startup_stage?: string | null;
  needs?: string[] | null;
  skills_offered?: string[] | null;
};
const MATCH_TAGS = [
  'AI / Machine Learning',
  'Software Development',
  'Product Development',
  'Sales & Marketing',
  'Investment & Finance',
  'Business Development',
  'Legal',
  'Operations',
  'Data Science',
  'Design',
] as const;

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('Expert');
  const [bio, setBio] = useState('');
  const [industry, setIndustry] = useState('');
  const [startupName, setStartupName] = useState('');
  const [hubName, setHubName] = useState('');
  const [startupStage, setStartupStage] = useState('');
  const [needs, setNeeds] = useState<string[]>([]);
  const [skillsOffered, setSkillsOffered] = useState<string[]>([]);

  const notify = (message: string) => Alert.alert('CommunityGraph', message);
  const toggleTag = (
  tag: string,
  selected: string[],
  setSelected: React.Dispatch<React.SetStateAction<string[]>>
) => {
  if (selected.includes(tag)) {
    setSelected(selected.filter(item => item !== tag));
  } else if (selected.length < 3) {
    setSelected([...selected, tag]);
  } else {
    notify('En fazla 3 seçenek belirleyebilirsiniz.');
  }
};

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    }).catch(() => setLoading(false));

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, currentSession) => setSession(currentSession)
    );
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session?.user) return;
    let cancelled = false;

    async function loadProfile() {
      const { data, error } = await supabase
        .from('profiles')
        .select('full_name,role,bio,industry,startup_name,hub_name,startup_stage,needs,skills_offered')
        .eq('id', session!.user.id)
        .maybeSingle();

      if (cancelled) return;
      if (error) {
        notify(error.message);
        return;
      }

      const profile = data as Profile | null;
      setName(profile?.full_name ?? '');
      setRole(profile?.role ?? 'Expert');
      setBio(profile?.bio ?? '');
      setIndustry(profile?.industry ?? '');
      setStartupName(profile?.startup_name ?? '');
      setHubName(profile?.hub_name ?? '');
      setStartupStage(profile?.startup_stage ?? '');
      setNeeds(profile?.needs ?? []);
      setSkillsOffered(profile?.skills_offered ?? []);
    }

    loadProfile();
    return () => { cancelled = true; };
  }, [session?.user.id]);

  async function authenticate() {
    if (!email.trim() || !password) {
      notify('E-posta ve şifre gerekli.');
      return;
    }

    setBusy(true);
    try {
      if (signup) {
        const { error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: { full_name: name.trim(), role },
          },
        });
        if (error) throw error;
        notify('Kayıt isteği alındı. E-posta doğrulaması gerekiyorsa gelen kutunu kontrol et.');
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
      }
    } catch (e: any) {
      notify(e.message ?? 'İşlem başarısız.');
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile() {
    if (!session?.user) return;
    setBusy(true);
    try {
      const { error } = await supabase.from('profiles').upsert({
        id: session.user.id,
        full_name: name.trim(),
        role,
        bio: bio.trim(),
        industry: industry.trim(),
        startup_name: startupName.trim(),
        hub_name: hubName.trim(),
        startup_stage: startupStage.trim(),
        needs: needs,
        skills_offered: skillsOffered,
      }, { onConflict: 'id' });

      if (error) throw error;
      notify('Profil kaydedildi.');
    } catch (e: any) {
      notify(e.message ?? 'Profil kaydedilemedi.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <View style={styles.center}><ActivityIndicator size="large" /></View>;
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.logo}>🌐 CommunityGraph</Text>
      <Text style={styles.subtitle}>
        Map the network. Decode the problem. Match the solver.
      </Text>

      {!session ? (
        <View style={styles.card}>
          <Text style={styles.heading}>{signup ? 'Create Account' : 'Welcome Back'}</Text>
          {signup && (
            <TextInput style={styles.input} placeholder="Full name"
              value={name} onChangeText={setName} />
          )}
          <TextInput style={styles.input} placeholder="Email"
            autoCapitalize="none" keyboardType="email-address"
            value={email} onChangeText={setEmail} />
          <TextInput style={styles.input} placeholder="Password"
            secureTextEntry value={password} onChangeText={setPassword} />
          {signup && (
            <TouchableOpacity style={styles.secondary}
              onPress={() => setRole(role === 'Expert' ? 'Founder' : 'Expert')}>
              <Text>Role: {role} (tap to change)</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.button}
            disabled={busy} onPress={authenticate}>
            <Text style={styles.buttonText}>
              {busy ? 'Please wait...' : signup ? 'Sign Up' : 'Login'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setSignup(!signup)}>
            <Text style={styles.link}>
              {signup ? 'Already have an account? Login' : 'New here? Sign Up'}
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
        <View style={styles.card}>
          <Text style={styles.heading}>My Profile</Text>
          <Text style={styles.email}>{session.user.email}</Text>
          <TextInput style={styles.input} placeholder="Full name"
            value={name} onChangeText={setName} />
          <TouchableOpacity style={styles.secondary}
            onPress={() => setRole(role === 'Expert' ? 'Founder' : 'Expert')}>
            <Text>Role: {role} (tap to change)</Text>
          </TouchableOpacity>
          <TextInput style={styles.input} placeholder="Industry"
            value={industry} onChangeText={setIndustry} />
            <TextInput
  style={styles.input}
  placeholder="Startup Name"
  value={startupName}
  onChangeText={setStartupName}
/>
<TextInput
  style={styles.input}
  placeholder="Hub / Community"
  value={hubName}
  onChangeText={setHubName}
/>
<TextInput
  style={styles.input}
  placeholder="Startup Stage (Idea / MVP / Growth)"
  value={startupStage}
  onChangeText={setStartupStage}
/>
          <TextInput style={[styles.input, styles.multiline]}
            placeholder="About you" multiline
            value={bio} onChangeText={setBio} />
             <Text style={styles.heading}>My Needs (max 3)</Text>
{MATCH_TAGS.map(tag => (
  <TouchableOpacity
    key={`need-${tag}`}
    style={[
      styles.secondary,
      { marginBottom: 6, backgroundColor: needs.includes(tag) ? '#DDEBFF' : '#F1F0FA' }
    ]}
    onPress={() => toggleTag(tag, needs, setNeeds)}
  >
    <Text>{needs.includes(tag) ? '✓ ' : '+ '}{tag}</Text>
   </TouchableOpacity>
))}
<Text style={styles.heading}>My Skills (max 3)</Text>
{MATCH_TAGS.map(tag => (
  <TouchableOpacity
    key={`skill-${tag}`}
    style={[
      styles.secondary,
      {
        marginBottom: 6,
        backgroundColor: skillsOffered.includes(tag)
          ? '#DDEBFF'
          : '#F1F0FA',
      },
    ]}
    onPress={() => toggleTag(tag, skillsOffered, setSkillsOffered)}
  >
    <Text>
      {skillsOffered.includes(tag) ? '✓ ' : '+ '}
      {tag}
    </Text>
  </TouchableOpacity>
))}
          <TouchableOpacity style={styles.button}
            disabled={busy} onPress={saveProfile}>
            <Text style={styles.buttonText}>

              {busy ? 'Saving...' : 'Save Profile'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => supabase.auth.signOut()}>
            <Text style={styles.link}>Logout</Text>
          </TouchableOpacity>
        </View>
        <AIAnalysis accessToken={session.access_token} />
        <Projects userId={session.user.id} />
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1, justifyContent: 'center', padding: 24,
    backgroundColor: '#F5F6FC',
  },
  center: { flex: 1, justifyContent: 'center' },
  logo: { fontSize: 29, fontWeight: '800', textAlign: 'center', color: '#4030A0' },
  subtitle: { textAlign: 'center', color: '#666', marginTop: 8, marginBottom: 28 },
  card: { backgroundColor: '#FFF', padding: 24, borderRadius: 18, gap: 14 },
  heading: { fontSize: 24, fontWeight: '700', marginBottom: 8 },
  email: { color: '#666', marginBottom: 8 },
  input: { borderWidth: 1, borderColor: '#DDD', padding: 14, borderRadius: 10 },
  multiline: { height: 100, textAlignVertical: 'top' },
  button: { backgroundColor: '#5542C8', padding: 16, borderRadius: 10 },
  buttonText: { color: '#FFF', textAlign: 'center', fontWeight: '700' },
  secondary: { padding: 12, backgroundColor: '#F1F0FA', borderRadius: 10 },
  link: { textAlign: 'center', color: '#5542C8', marginTop: 8 },
});
