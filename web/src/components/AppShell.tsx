import {
  AppShell,
  Badge,
  Box,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'

export function KithaironAppShell() {
  return (
    <AppShell
      className="app-root"
      header={{ height: 58 }}
      navbar={{ width: 300, breakpoint: 'sm' }}
      padding="md"
    >
      <AppShell.Header className="app-header">
        <Group h="100%" px="md" justify="space-between">
          <Box>
            <Title order={1} className="app-title">
              Kithairon Visualizer
            </Title>
            <Text className="app-subtitle">Canon candidate workspace</Text>
          </Box>
          <Badge variant="light" color="teal">
            API-backed
          </Badge>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className="app-navbar" p="md">
        <Stack gap="md">
          <Paper className="candidate-surface" p="md">
            <Text className="surface-title">Run</Text>
          </Paper>
          <Paper className="candidate-surface" p="md">
            <Text className="surface-title">Candidates</Text>
          </Paper>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box className="workspace-grid">
          <Stack gap="md">
            <Paper className="score-surface" mih={340} p="md">
              <Text className="surface-title">Score</Text>
            </Paper>
            <Paper className="roll-surface" mih={240} p="md">
              <Text className="surface-title">Piano Roll</Text>
            </Paper>
          </Stack>
          <Paper className="inspector-surface" mih={596} p="md">
            <Text className="surface-title">Inspector</Text>
          </Paper>
        </Box>
      </AppShell.Main>
    </AppShell>
  )
}
