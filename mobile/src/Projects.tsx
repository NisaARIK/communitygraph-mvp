import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, ScrollView,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { supabase } from './supabase';

type Project = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  project_type: string;
  industry: string;
  required_skills: string[];
  status: string;
  created_at: string;
};

const TYPES = [
  'All', 'Academic', 'Open Source',
  'Social Impact', 'Startup', 'Other',
];

export default function Projects({ userId }: { userId: string }) {
  const [page, setPage] = useState<'discover' | 'create' | 'detail'>('discover');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('Academic');
  const [industry, setIndustry] = useState('');
  const [skills, setSkills] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError('');
    const { data, error: requestError } = await supabase
      .from('projects')
      .select('id,owner_id,title,description,project_type,industry,required_skills,status,created_at')
      .order('created_at', { ascending: false })
      .limit(100);

    if (requestError) setError(requestError.message);
    else setProjects((data ?? []) as Project[]);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  async function createProject() {
    const cleanTitle = title.trim();
    const cleanDescription = description.trim();

    if (cleanTitle.length < 3 || cleanTitle.length > 150) {
      Alert.alert('Validation', 'Title must contain 3–150 characters.');
      return;
    }
    if (cleanDescription.length < 10 || cleanDescription.length > 5000) {
      Alert.alert('Validation', 'Description must contain 10–5000 characters.');
      return;
    }

    const skillList = [...new Set(
      skills.split(',').map(s => s.trim()).filter(Boolean)
    )];

    setSaving(true);
    const { data, error: insertError } = await supabase
      .from('projects')
      .insert({
        owner_id: userId,
        title: cleanTitle,
        description: cleanDescription,
        project_type: type,
        industry: industry.trim(),
        required_skills: skillList,
        status: 'Open',
      })
      .select('id')
      .single();

    setSaving(false);

    if (insertError) {
      Alert.alert('Could not create project', insertError.message);
      return;
    }

    if (!data?.id) {
      Alert.alert('Error', 'Project creation could not be verified.');
      return;
    }

    setTitle('');
    setDescription('');
    setIndustry('');
    setSkills('');
    setType('Academic');
    setFilter('All');
    setSearch('');
    setPage('discover');
    await loadProjects();
    Alert.alert('Success', 'Project created successfully.');
  }

  const visibleProjects = projects.filter(p => {
    const matchesType = filter === 'All' || p.project_type === filter;
    const query = search.trim().toLowerCase();
    const matchesSearch = !query ||
      p.title.toLowerCase().includes(query) ||
      p.description.toLowerCase().includes(query) ||
      (p.industry ?? '').toLowerCase().includes(query);
    return matchesType && matchesSearch;
  });

  const button = (label: string, onPress: () => void, active = false) => (
    <TouchableOpacity
      onPress={onPress}
      style={[styles.smallButton, active && styles.activeButton]}
    >
      <Text style={[styles.smallButtonText, active && styles.activeText]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>CommunityGraph Projects</Text>

      <View style={styles.navigation}>
        {button('Discover', () => {
          setPage('discover');
          loadProjects();
        }, page === 'discover')}
        {button('Create Project', () => setPage('create'), page === 'create')}
      </View>

      {page === 'create' && (
        <View style={styles.card}>
          <Text style={styles.title}>Create a Project</Text>
          <TextInput
            style={styles.input}
            placeholder="Project title"
            value={title}
            onChangeText={setTitle}
            maxLength={150}
          />
          <TextInput
            style={[styles.input, styles.description]}
            placeholder="Describe your project"
            multiline
            value={description}
            onChangeText={setDescription}
            maxLength={5000}
          />
          <Text style={styles.label}>Project category</Text>
          <View style={styles.chips}>
            {TYPES.filter(t => t !== 'All').map(t => (
              <React.Fragment key={t}>
                {button(t, () => setType(t), type === t)}
              </React.Fragment>
            ))}
          </View>
          <TextInput
            style={styles.input}
            placeholder="Industry / field"
            value={industry}
            onChangeText={setIndustry}
          />
          <TextInput
            style={styles.input}
            placeholder="Required skills (Python, ML, Design)"
            value={skills}
            onChangeText={setSkills}
          />
          <TouchableOpacity
            disabled={saving}
            style={[styles.primaryButton, saving && styles.disabled]}
            onPress={createProject}
          >
            <Text style={styles.primaryText}>
              {saving ? 'Creating...' : 'Publish Project'}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {page === 'discover' && (
        <View>
          <TextInput
            style={styles.input}
            placeholder="Search projects..."
            value={search}
            onChangeText={setSearch}
          />
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.chips}>
              {TYPES.map(t => (
                <React.Fragment key={t}>
                  {button(t, () => setFilter(t), filter === t)}
                </React.Fragment>
              ))}
            </View>
          </ScrollView>

          {button('Refresh projects', loadProjects)}
          {loading && <ActivityIndicator style={{ margin: 16 }} />}
          {!!error && <Text style={styles.error}>{error}</Text>}

          {!loading && !error && (
            <FlatList
              data={visibleProjects}
              keyExtractor={item => item.id}
              scrollEnabled={false}
              ListEmptyComponent={
                <Text style={styles.muted}>No matching projects found.</Text>
              }
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.card}
                  onPress={() => {
                    setSelected(item);
                    setPage('detail');
                  }}
                >
                  <Text style={styles.title}>{item.title}</Text>
                  <Text style={styles.muted}>
                    {item.project_type} · {item.status}
                  </Text>
                  <Text numberOfLines={3}>{item.description}</Text>
                  <Text style={styles.link}>View details →</Text>
                </TouchableOpacity>
              )}
            />
          )}
        </View>
      )}

      {page === 'detail' && selected && (
        <View style={styles.card}>
          {button('← Back to projects', () => setPage('discover'))}
          <Text style={styles.title}>{selected.title}</Text>
          <Text style={styles.muted}>
            {selected.project_type} · {selected.status}
          </Text>
          <Text style={styles.label}>Description</Text>
          <Text>{selected.description}</Text>
          <Text style={styles.label}>Industry</Text>
          <Text>{selected.industry || 'Not specified'}</Text>
          <Text style={styles.label}>Required skills</Text>
          <Text>
            {selected.required_skills?.join(', ') || 'Not specified'}
          </Text>
          <Text style={styles.label}>Ownership</Text>
          <Text>
            {selected.owner_id === userId
              ? 'Your project'
              : 'Community project'}
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 28, gap: 14 },
  heading: { fontSize: 23, fontWeight: '800', color: '#4030A0' },
  navigation: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  card: {
    backgroundColor: '#FFF', borderRadius: 16,
    padding: 18, marginTop: 12, gap: 12,
  },
  title: { fontSize: 19, fontWeight: '700' },
  label: { fontWeight: '700', marginTop: 8 },
  muted: { color: '#777' },
  link: { color: '#5542C8', fontWeight: '700' },
  input: {
    borderWidth: 1, borderColor: '#DDD',
    borderRadius: 10, padding: 12,
    backgroundColor: '#FFF', marginTop: 10,
  },
  description: { minHeight: 110, textAlignVertical: 'top' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 7, paddingVertical: 8 },
  smallButton: {
    paddingHorizontal: 12, paddingVertical: 10,
    borderRadius: 10, backgroundColor: '#EAE8F5',
  },
  activeButton: { backgroundColor: '#5542C8' },
  smallButtonText: { color: '#4030A0', fontWeight: '600' },
  activeText: { color: '#FFF' },
  primaryButton: {
    backgroundColor: '#5542C8', borderRadius: 10,
    padding: 16, marginTop: 12,
  },
  primaryText: { color: '#FFF', textAlign: 'center', fontWeight: '700' },
  disabled: { opacity: 0.5 },
  error: { color: '#B00020', marginTop: 12 },
});
