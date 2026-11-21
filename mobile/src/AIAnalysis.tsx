import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';

type AIAnalysisProps = {
  accessToken: string;
};

export default function AIAnalysis({ accessToken }: AIAnalysisProps) {
  const [description, setDescription] = useState('');
  const [result, setResult] = useState<{
  industry: string;
  required_skills: string[];
  expert_roles: string[];
} | null>(null);

const [error, setError] = useState('');
type ExpertMatch = {
  id: string | null;
  name: string;
  role: string;
  score: number;
  matched_skills: string[];
  missing_skills: string[];
};

const [matches, setMatches] = useState<ExpertMatch[]>([]);
const [matchingError, setMatchingError] = useState('');

const analyzeProblem = async () => {
    alert('AI butonuna basıldı');
  if (description.trim().length < 10) {
    setError('Lütfen en az 10 karakterlik bir açıklama yaz.');
    return;
  }

  setLoading(true);
  setError('');
  setResult(null);

  try {
    const apiUrl = process.env.EXPO_PUBLIC_AI_API_URL;

    if (!apiUrl) {
      throw new Error('AI API adresi bulunamadı.');
    }

    const response = await fetch(`${apiUrl.replace(/\/$/, '')}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        description: description.trim(),
      }),
    });

    if (!response.ok) {
      throw new Error(`AI analizi başarısız: HTTP ${response.status}`);
    }

   const data = await response.json();
setResult(data);

setMatches([]);
setMatchingError('');

try {
  const matchResponse = await fetch(
    `${apiUrl.replace(/\/$/, '')}/recommend-experts`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        industry: data.industry,
        required_skills: data.required_skills,
      }),
    }
  );

  if (!matchResponse.ok) {
    throw new Error(
      `Uzman eşleştirme hatası: HTTP ${matchResponse.status}`
    );
  }

  const matchData = await matchResponse.json();
  setMatches(matchData.matches ?? []);

} catch (matchErr) {
  setMatchingError(
    matchErr instanceof Error
      ? matchErr.message
      : 'Uzman önerileri alınamadı.'
  );
}
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Bir hata oluştu.');
  } finally {
    setLoading(false);
  }
};
  const [loading, setLoading] = useState(false);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>CommunityGraph AI</Text>

      <Text style={styles.subtitle}>
        Projeni veya çözmek istediğin problemi anlat.
      </Text>

      <TextInput
        style={styles.input}
        multiline
        placeholder="Proje fikrini buraya yaz..."
        value={description}
        onChangeText={setDescription}
      />

      <TouchableOpacity
  style={styles.button}
  disabled={loading}
  onPress={analyzeProblem}
>
        {loading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.buttonText}>AI ile Analiz Et</Text>
        )}
      </TouchableOpacity>
      {error ? (
  <Text style={{ color: 'red', marginTop: 12 }}>
    {error}
  </Text>
) : null}

{result && (
  <View style={{ marginTop: 20 }}>
    <Text style={styles.title}>AI Analiz Sonucu</Text>

    <Text style={{ fontWeight: 'bold', marginTop: 10 }}>
      Sektör
    </Text>
    <Text>{result.industry}</Text>

    <Text style={{ fontWeight: 'bold', marginTop: 10 }}>
      Gerekli Beceriler
    </Text>
    {result.required_skills.map((skill, index) => (
      <Text key={index}>• {skill}</Text>
    ))}

    <Text style={{ fontWeight: 'bold', marginTop: 10 }}>
      Uzman Rolleri
    </Text>
    {result.expert_roles.map((role, index) => (
      <Text key={index}>• {role}</Text>
    ))}
    <Text style={{ fontWeight: 'bold', marginTop: 20, fontSize: 17 }}>
  En Uygun 3 Uzman
</Text>

{matches.map((expert, index) => (
  <View
    key={expert.id ?? `expert-${index}`}
    style={{
      backgroundColor: '#FFFFFF',
      padding: 14,
      borderRadius: 12,
      marginTop: 10,
      borderWidth: 1,
      borderColor: '#E5E7EB',
    }}
  >
    <Text style={{ fontWeight: 'bold', fontSize: 16 }}>
      {expert.name}
    </Text>

    <Text>{expert.role}</Text>

    <Text style={{ color: '#4030A0', marginTop: 6 }}>
      Eşleşme: %{Math.round(expert.score * 100)}
    </Text>

    <Text style={{ marginTop: 6 }}>
      Eşleşen beceriler: {expert.matched_skills.join(', ') || 'Yok'}
    </Text>
  </View>
))}

{matches.length === 0 && !matchingError && (
  <Text style={{ marginTop: 10 }}>
    Uygun uzman bulunamadı.
  </Text>
)}

{matchingError !== '' && (
  <Text style={{ color: '#B91C1C', marginTop: 10 }}>
    {matchingError}
  </Text>
)}
  </View>
)}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#F5F6FC',
    borderRadius: 16,
    marginVertical: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#4030A0',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 14,
    marginBottom: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: '#D5D5E5',
    borderRadius: 10,
    padding: 12,
    minHeight: 120,
    textAlignVertical: 'top',
    backgroundColor: '#FFFFFF',
  },
  button: {
    backgroundColor: '#4030A0',
    padding: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
});