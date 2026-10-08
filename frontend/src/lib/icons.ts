// Registro de iconos de la interfaz. Los nombres son nuestros (qué significa
// el icono), no los de Lucide: cambiar el dibujo de "delete" o pasar a un set
// propio es tocar solo este mapa. Se importa cada icono por su ruta para que
// el bundle lleve solo los que aparecen aquí.
import type { Component } from 'svelte';

import AlertTriangle from '@lucide/svelte/icons/triangle-alert';
import Apple from '@lucide/svelte/icons/apple';
import ArrowLeft from '@lucide/svelte/icons/arrow-left';
import ArrowRight from '@lucide/svelte/icons/arrow-right';
import Bean from '@lucide/svelte/icons/bean';
import Beef from '@lucide/svelte/icons/beef';
import Beer from '@lucide/svelte/icons/beer';
import Bell from '@lucide/svelte/icons/bell';
import BellOff from '@lucide/svelte/icons/bell-off';
import BookOpen from '@lucide/svelte/icons/book-open';
import Bug from '@lucide/svelte/icons/bug';
import CalendarDays from '@lucide/svelte/icons/calendar-days';
import Camera from '@lucide/svelte/icons/camera';
import ChartColumn from '@lucide/svelte/icons/chart-column';
import Check from '@lucide/svelte/icons/check';
import ChefHat from '@lucide/svelte/icons/chef-hat';
import ChevronDown from '@lucide/svelte/icons/chevron-down';
import ChevronUp from '@lucide/svelte/icons/chevron-up';
import CircleCheck from '@lucide/svelte/icons/circle-check';
import Clock from '@lucide/svelte/icons/clock';
import Compass from '@lucide/svelte/icons/compass';
import CookingPot from '@lucide/svelte/icons/cooking-pot';
import Croissant from '@lucide/svelte/icons/croissant';
import Crown from '@lucide/svelte/icons/crown';
import CupSoda from '@lucide/svelte/icons/cup-soda';
import Droplet from '@lucide/svelte/icons/droplet';
import Droplets from '@lucide/svelte/icons/droplets';
import Drumstick from '@lucide/svelte/icons/drumstick';
import Dumbbell from '@lucide/svelte/icons/dumbbell';
import Egg from '@lucide/svelte/icons/egg';
import EggFried from '@lucide/svelte/icons/egg-fried';
import Fish from '@lucide/svelte/icons/fish';
import Flame from '@lucide/svelte/icons/flame';
import Flower from '@lucide/svelte/icons/flower';
import Flower2 from '@lucide/svelte/icons/flower-2';
import Footprints from '@lucide/svelte/icons/footprints';
import Globe from '@lucide/svelte/icons/globe';
import Hand from '@lucide/svelte/icons/hand';
import Heart from '@lucide/svelte/icons/heart';
import HeartHandshake from '@lucide/svelte/icons/heart-handshake';
import Info from '@lucide/svelte/icons/info';
import Hourglass from '@lucide/svelte/icons/hourglass';
import House from '@lucide/svelte/icons/house';
import InfinityIcon from '@lucide/svelte/icons/infinity';
import LayoutGrid from '@lucide/svelte/icons/layout-grid';
import Leaf from '@lucide/svelte/icons/leaf';
import Link from '@lucide/svelte/icons/link';
import Lock from '@lucide/svelte/icons/lock';
import LockOpen from '@lucide/svelte/icons/lock-open';
import LogOut from '@lucide/svelte/icons/log-out';
import Mail from '@lucide/svelte/icons/mail';
import MapPin from '@lucide/svelte/icons/map-pin';
import Megaphone from '@lucide/svelte/icons/megaphone';
import Milk from '@lucide/svelte/icons/milk';
import Moon from '@lucide/svelte/icons/moon';
import NotebookPen from '@lucide/svelte/icons/notebook-pen';
import Nut from '@lucide/svelte/icons/nut';
import Package from '@lucide/svelte/icons/package';
import PackageOpen from '@lucide/svelte/icons/package-open';
import Paperclip from '@lucide/svelte/icons/paperclip';
import Pencil from '@lucide/svelte/icons/pencil';
import Pill from '@lucide/svelte/icons/pill';
import Plus from '@lucide/svelte/icons/plus';
import Refrigerator from '@lucide/svelte/icons/refrigerator';
import Ruler from '@lucide/svelte/icons/ruler';
import Salad from '@lucide/svelte/icons/salad';
import Sandwich from '@lucide/svelte/icons/sandwich';
import Swords from '@lucide/svelte/icons/swords';
import Scale from '@lucide/svelte/icons/scale';
import ScanBarcode from '@lucide/svelte/icons/scan-barcode';
import ScrollText from '@lucide/svelte/icons/scroll-text';
import Search from '@lucide/svelte/icons/search';
import Send from '@lucide/svelte/icons/send';
import Settings from '@lucide/svelte/icons/settings';
import Share2 from '@lucide/svelte/icons/share-2';
import Shell from '@lucide/svelte/icons/shell';
import ShoppingCart from '@lucide/svelte/icons/shopping-cart';
import Shrimp from '@lucide/svelte/icons/shrimp';
import Smile from '@lucide/svelte/icons/smile';
import Snowflake from '@lucide/svelte/icons/snowflake';
import Sparkles from '@lucide/svelte/icons/sparkles';
import Sprout from '@lucide/svelte/icons/sprout';
import Star from '@lucide/svelte/icons/star';
import Stethoscope from '@lucide/svelte/icons/stethoscope';
import Target from '@lucide/svelte/icons/target';
import Trash2 from '@lucide/svelte/icons/trash-2';
import TrendingUp from '@lucide/svelte/icons/trending-up';
import Trophy from '@lucide/svelte/icons/trophy';
import Undo2 from '@lucide/svelte/icons/undo-2';
import Upload from '@lucide/svelte/icons/upload';
import User from '@lucide/svelte/icons/user';
import Forward from '@lucide/svelte/icons/forward';
import Users from '@lucide/svelte/icons/users';
import Utensils from '@lucide/svelte/icons/utensils';
import Wheat from '@lucide/svelte/icons/wheat';
import WifiOff from '@lucide/svelte/icons/wifi-off';
import Wine from '@lucide/svelte/icons/wine';
import X from '@lucide/svelte/icons/x';
import ChevronRight from '@lucide/svelte/icons/chevron-right';
import Power from '@lucide/svelte/icons/power';
import ListChecks from '@lucide/svelte/icons/list-checks';
import BicepsFlexed from '@lucide/svelte/icons/biceps-flexed';
import Activity from '@lucide/svelte/icons/activity';
import Volleyball from '@lucide/svelte/icons/volleyball';
import Music from '@lucide/svelte/icons/music';
import Mountain from '@lucide/svelte/icons/mountain';
import PersonStanding from '@lucide/svelte/icons/person-standing';
import Waves from '@lucide/svelte/icons/waves';
import Bike from '@lucide/svelte/icons/bike';
import RollerCoaster from '@lucide/svelte/icons/roller-coaster';
import BrushCleaning from '@lucide/svelte/icons/brush-cleaning';
import Coffee from '@lucide/svelte/icons/coffee';
import Laugh from '@lucide/svelte/icons/laugh';
import Meh from '@lucide/svelte/icons/meh';
import Frown from '@lucide/svelte/icons/frown';
import BatteryLow from '@lucide/svelte/icons/battery-low';
import Medal from '@lucide/svelte/icons/medal';
import Pizza from '@lucide/svelte/icons/pizza';
import TrendingDown from '@lucide/svelte/icons/trending-down';
import UserPlus from '@lucide/svelte/icons/user-plus';
import TreeDeciduous from '@lucide/svelte/icons/tree-deciduous';
import Venus from '@lucide/svelte/icons/venus';
import Mars from '@lucide/svelte/icons/mars';
import Copy from '@lucide/svelte/icons/copy';
import Calculator from '@lucide/svelte/icons/calculator';
import Zap from '@lucide/svelte/icons/zap';

export const ICONS = {
	// Acciones
	add: Plus,
	close: X,
	check: Check,
	edit: Pencil,
	delete: Trash2,
	share: Share2,
	export: Upload,
	link: Link,
	camera: Camera,
	scan: ScanBarcode,
	search: Search,
	star: Star,
	undo: Undo2,
	back: ArrowLeft,
	forward: ArrowRight,
	up: ChevronUp,
	down: ChevronDown,
	send: Send,
	logout: LogOut,
	// Estados y avisos
	lock: Lock,
	unlock: LockOpen,
	warning: AlertTriangle,
	success: CircleCheck,
	sparkles: Sparkles,
	bell: Bell,
	bellOff: BellOff,
	trial: Hourglass,
	pending: Hourglass,
	premium: Crown,
	tap: Hand,
	info: Info,
	attach: Paperclip,
	offline: WifiOff,
	// Personas
	user: User,
	users: Users,
	forPartner: Forward,
	partner: Heart,
	couple: HeartHandshake,
	// Secciones
	diary: NotebookPen,
	history: CalendarDays,
	recipes: BookOpen,
	exercise: Dumbbell,
	weight: Scale,
	measurements: Ruler,
	settings: Settings,
	goals: Target,
	modules: LayoutGrid,
	supplements: Pill,
	mood: Smile,
	water: Droplet,
	steps: Footprints,
	streak: Flame,
	quick: Zap,
	recent: Clock,
	inventory: Package,
	empty: PackageOpen,
	shopping: ShoppingCart,
	home: House,
	fridge: Refrigerator,
	freezer: Snowflake,
	location: MapPin,
	stats: ChartColumn,
	trend: TrendingUp,
	trophy: Trophy,
	duel: Swords,
	unlimited: InfinityIcon,
	night: Moon,
	globe: Globe,
	mail: Mail,
	announce: Megaphone,
	bug: Bug,
	diagnostics: Stethoscope,
	compass: Compass,
	legal: ScrollText,
	cook: ChefHat,
	// Comida
	meal: Utensils,
	breakfast: EggFried,
	salad: Salad,
	pot: CookingPot,
	grain: Wheat,
	chicken: Drumstick,
	milk: Milk,
	egg: Egg,
	fruit: Apple,
	meat: Beef,
	fish: Fish,
	bread: Croissant,
	sandwich: Sandwich,
	drink: CupSoda,
	beer: Beer,
	oil: Droplets,
	// Alérgenos
	nut: Nut,
	bean: Bean,
	shrimp: Shrimp,
	shell: Shell,
	leaf: Leaf,
	sprout: Sprout,
	wine: Wine,
	flower: Flower,
	flower2: Flower2,
	calc: Calculator,
	copy: Copy,
	male: Mars,
	female: Venus,
	treeNut: TreeDeciduous,
	userPlus: UserPlus,
	trendDown: TrendingDown,
	cheat: Pizza,
	medal: Medal,
	batteryLow: BatteryLow,
	frown: Frown,
	meh: Meh,
	laugh: Laugh,
	coffee: Coffee,
	sweep: BrushCleaning,
	comeback: RollerCoaster,
	bike: Bike,
	swim: Waves,
	stretch: PersonStanding,
	climb: Mountain,
	dance: Music,
	sport: Volleyball,
	run: Activity,
	strength: BicepsFlexed,
	checklist: ListChecks,
	power: Power,
	chevronRight: ChevronRight
} satisfies Record<string, Component<any>>;

export type IconName = keyof typeof ICONS;
