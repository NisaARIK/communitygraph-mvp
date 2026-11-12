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

type Profile = {
  full_name: string | null;
  role: string | null;
  bio: string | null;
  industry: string | null;
};

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

  const notify = (message: string) => Alert.alert('CommunityGraph', message);

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
        .select('full_name,role,bio,industry')
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
        Connect people. Build projects. Solve problems.
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
          <TextInput style={[styles.input, styles.multiline]}
            placeholder="About you" multiline
            value={bio} onChangeText={setBio} />
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
