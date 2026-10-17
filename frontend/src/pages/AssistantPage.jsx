import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { AssessmentIcon, AutoAwesomeIcon, MessageIcon, ShieldIcon } from '../components/Icons';
import { useAuth } from '../auth/AuthContext';
import { displayError } from '../utils';

export default function AssistantPage() {
  const { user, request } = useAuth();
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello ${user?.full_name || 'there'}! I am your AI attendance assistant. Ask me questions about verified attendance summaries, monthly trends, or absenteeism rates.`,
    },
  ]);

  const quickPrompts = user?.role === 'admin'
    ? [
        'What is the attendance summary for 2026-10?',
        'What is the organization absenteeism rate for 2026-10?',
        'Show attendance trends for 2026-10',
      ]
    : [
        'What was my attendance summary for 2026-10?',
        'What is my absenteeism rate for 2026-10?',
        'Show my attendance trends for 2026-10',
      ];

  const handleSend = async (queryToSend) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || loading) return;

    setError('');
    const userMessageId = `user-${Date.now()}`;
    const newMessages = [
      ...messages,
      { id: userMessageId, role: 'user', content: text },
    ];
    setMessages(newMessages);
    setInputQuery('');
    setLoading(true);

    try {
      const response = await request('/api/v1/assistant/query', {
        method: 'POST',
        body: { query: text },
      });

      const assistantMessageId = `assistant-${Date.now()}`;
      setMessages([
        ...newMessages,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: response.answer,
          toolsUsed: response.tools_used || [],
          reportData: response.report_data,
        },
      ]);
    } catch (err) {
      setError(displayError(err, 'Unable to query the assistant. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ maxWidth: 960, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2.5 }}>
        <Box>
          <Typography variant="overline" color="primary.main" fontWeight={800}>
            ASSISTANT
          </Typography>
          <Typography variant="h4" color="primary.dark">
            Attendance assistant
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Natural language insights powered by Groq and verified report services.
          </Typography>
        </Box>
        <Chip
          icon={<ShieldIcon sx={{ fontSize: '1rem !important' }} />}
          label="PII masked · Read-only tools"
          size="small"
          color="primary"
          variant="outlined"
          sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
        />
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack spacing={2.5}>
            {messages.map((msg) => (
              <Box
                key={msg.id}
                sx={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    maxWidth: { xs: '100%', sm: '85%' },
                    borderRadius: 3,
                    bgcolor: msg.role === 'user' ? 'primary.main' : '#f8fafc',
                    color: msg.role === 'user' ? '#ffffff' : 'text.primary',
                    border: msg.role === 'user' ? 'none' : '1px solid #e2e8f0',
                  }}
                >
                  <Stack direction="row" spacing={1.5} alignItems="flex-start">
                    {msg.role === 'assistant' && (
                      <Box
                        sx={{
                          width: 32,
                          height: 32,
                          display: 'grid',
                          placeItems: 'center',
                          borderRadius: '50%',
                          bgcolor: '#fff3df',
                          color: 'secondary.dark',
                          flexShrink: 0,
                          mt: 0.25,
                        }}
                      >
                        <AutoAwesomeIcon sx={{ fontSize: 18 }} />
                      </Box>
                    )}
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography
                        variant="body1"
                        sx={{
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                        }}
                      >
                        {msg.content}
                      </Typography>

                      {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                        <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 0.75 }}>
                          {msg.toolsUsed.map((tool) => (
                            <Chip
                              key={tool}
                              size="small"
                              icon={<AssessmentIcon sx={{ fontSize: '0.9rem !important' }} />}
                              label={`Tool: ${tool}`}
                              sx={{ bgcolor: '#eef4f8', color: 'primary.dark', fontSize: '0.75rem' }}
                            />
                          ))}
                        </Stack>
                      )}

                      {msg.reportData && !msg.reportData.error && (
                        <Paper
                          variant="outlined"
                          sx={{
                            mt: 1.5,
                            p: 1.5,
                            bgcolor: '#ffffff',
                            borderRadius: 2,
                            borderColor: '#e2e8f0',
                          }}
                        >
                          <Typography variant="caption" fontWeight={700} color="text.secondary" display="block">
                            Verified Report Metrics ({msg.reportData.month || 'Selected Period'})
                          </Typography>
                          <Stack direction="row" spacing={2} sx={{ mt: 0.5, flexWrap: 'wrap', gap: 1 }}>
                            {msg.reportData.attendance_rate !== undefined && (
                              <Typography variant="body2">
                                <strong>Attendance Rate:</strong> {msg.reportData.attendance_rate != null ? `${msg.reportData.attendance_rate}%` : 'N/A'}
                              </Typography>
                            )}
                            {msg.reportData.present_employee_days !== undefined && (
                              <Typography variant="body2">
                                <strong>Present Days:</strong> {msg.reportData.present_employee_days} / {msg.reportData.expected_employee_days}
                              </Typography>
                            )}
                            {msg.reportData.incomplete_employee_days !== undefined && (
                              <Typography variant="body2">
                                <strong>Incomplete:</strong> {msg.reportData.incomplete_employee_days}
                              </Typography>
                            )}
                            {msg.reportData.absenteeism_rate !== undefined && (
                              <Typography variant="body2">
                                <strong>Absenteeism Rate:</strong> {msg.reportData.absenteeism_rate != null ? `${msg.reportData.absenteeism_rate}%` : 'N/A'}
                              </Typography>
                            )}
                          </Stack>
                        </Paper>
                      )}
                    </Box>
                  </Stack>
                </Paper>
              </Box>
            ))}

            {loading && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    bgcolor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                  }}
                >
                  <CircularProgress size={18} color="primary" />
                  <Typography variant="body2" color="text.secondary">
                    Retrieving verified records and consulting Groq AI…
                  </Typography>
                </Paper>
              </Box>
            )}
          </Stack>
        </CardContent>
        <Divider />
        <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 0.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', whiteSpace: 'nowrap' }}>
                Suggestions:
              </Typography>
              {quickPrompts.map((prompt) => (
                <Chip
                  key={prompt}
                  label={prompt}
                  size="small"
                  onClick={() => handleSend(prompt)}
                  disabled={loading}
                  sx={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
                />
              ))}
            </Stack>
            <Stack direction="row" spacing={1.5}>
              <TextField
                fullWidth
                size="small"
                placeholder="Ask about attendance rates, trends, or absenteeism (e.g., 'What was attendance in 2026-10?')"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <MessageIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                variant="contained"
                onClick={() => handleSend()}
                disabled={loading || !inputQuery.trim()}
                sx={{ px: 3, minWidth: 100 }}
              >
                {loading ? <CircularProgress size={20} color="inherit" /> : 'Send'}
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
