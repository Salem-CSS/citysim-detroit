# AWS logistics and how the AWS judge scores

Source recording: Important judging.m4a (15 min 22 s)

> Machine transcript of a phone recording made in a noisy room at BuilderWars (Newlab, Detroit, Nov 14, 2026).
> It contains errors: misheard words, dropped phrases and wrong product names. Timestamps are minutes:seconds into the recording.
> Check anything important against the recording or with the speaker.

## Key points

These are a reader's summary of the transcript below, with the same caveats.

**Accounts**
- Two separate AWS accounts: a workshop account provisioned for you (access code, for the Strands workshop only) and your own free-tier account, which is where the hackathon project is built.
- A new account gets free-tier credit (stated as $100, more after tutorials). If you already have an account, creating one more with a different email is fine; many accounts get flagged as fraud.
- You can design the whole code base before deploying; AWS infrastructure is the last step.
- Kiro is offered but optional; other coding assistants are fine.

**Judging (from about 05:15)**
- "Your job is to tell me why": for every design choice, why service A over B or C, and why it was implemented that way. Think about synergies between AWS services.
- Technology for its own sake earns nothing. Speed or sophistication that does not serve the problem gains no points.
- Start from the problem: a business case and a customer pain point, then work backwards to technology.
- At implementation, name the trade-offs: cost, resilience, regulation, security, personal data.
- Novelty matters less than a reasonable, relatable business problem that the solution addresses, with implementation choices you can explain.
- Example given: for image or face recognition, expect to be asked why you used an expensive generative AI service (Bedrock) when a cheaper purpose-built service (Rekognition) exists. Same for serverless versus not.

## Transcript

**[00:00]** exactly the steps that we're going to go through in terms of what is the workshop, what is the difference, how do you start building, and telling you exactly what to do. So hopefully a lot of people understand me. Awesome meeting all of you. And I told most of you, you start thinking about your idea, thinking about the use case, kind of having a problem statement, and working with your teams. So I'm going to be very--

**[00:25]** Logistics I think is super important. You need to know what you're doing. So I'm going to be as clear as I can and then if not, please ask any questions.

**[00:32]** All right, first and foremost, basically think of it like you're going to have two AWS accounts here, okay? One of them, you are going to just click a URL. It's going to take you to the AWS account. You're going to enter your access code and magically you're going to have your own AWS account that you can run this workshop on, okay? What is the workshop? The workshop is you are going to build an agent.

**[00:57]** using strands, okay, which is our agent framework, all right? In code, and you're gonna learn many of the concepts around how to build an agent, right? All right, so that's something that you can sort of understand. It's straightforward, and then it'll come to me if you need any help. If you need, you know, if you're struggling, if something's not working, that's the workshop side of it. But-- (static)

**[01:22]** I know you all want $500 so you don't care about the workshop side of it. You care about the hackathon side of it. So the hackathon side of it is you're also going to provision your own free tier AWS account. Who here has created an AWS account before? Okay, most of you have. If you are not in the free tier, which means you basically can create an AWS account, you'll get 100% free tier.

**[01:47]** $100 for free to use AWS services. You will not exceed $100 today, I promise, unless you really, really know what you're doing, but you won't and you shouldn't. If you do a couple of tutorials, you get even more credits. So this new building on AWS is going to be free for you today. If you exceed or you don't have another account, come talk to me. We have a way to help circumvent--

**[02:12]** that but please just if you haven't created an account use a new email to create one if you create one already create another one with a different email and you'll get back in the free tier. Don't create like 25 accounts because we'll flag you for fraud if you do that. So one or two totally fine three okay all right so that account that you create the free tier account completely separate from this workshop right so

**[02:37]** So, quiz question, true or false? Alright, raise your hand if it's true, keep your hand down if it's false. This workshop teaches you how to build agents and has nothing to do with the account that you're creating on AWS. Raise your hand if that's true.

**[02:53]** There you go, all right. Yeah, separate, completely separate. So this workshop is an account that I'm giving you, okay? I am provisioning that account for you. It's happened on what's called Workshop Studio in the background. We do hundreds and hundreds of events with millions of customers. We have a mechanism to give you accounts. You're then gonna create your own account. That's where you're gonna build, okay? Any questions on that so far?

**[03:19]** Alright. Building.

**[03:22]** I'll go through the workshop in detail in a minute, right? When you are building, you are also gonna get access to Hero. Okay? Hero is your coding assistant. I'm gonna pull up something right now that's going to walk you through how to access the workshop. I'm gonna show you how you can get free Hero credits and how to download Hero. So when you are building... (static)

**[03:46]** your workshop, or excuse me, your hackathon idea. You're going to use, you don't have to use Kero by the way, it's just if you use plot code already and you don't want to change, that's completely fine. But if you're new to agentic coding, I would just recommend using Kero, and then you can explore other areas, feel free to ask any questions. So that's gonna be how you're going to write your code, how you're gonna deploy to AWS if you wanna create a new code.

**[04:11]** database, right? Kiro is there to help you. If you're not that familiar with AWS services, I will talk a little bit about your AWS services, but you can come ask me for help. And when my colleague comes in with Lucas, we can sit and help each team. So that's why we're here. Okay. So once again, I'm going to share a website with you that has the workshop and Kiro. Okay. The only thing that you're going to be doing is creating

**[04:36]** your own AWS account.

**[04:40]** That is something you're going to do when you start building. Don't worry if you haven't done that yet. In fact, using Kierl or one of your coding assistants, you can actually IDA your entire code base before you even deploy into AWS. Just keep that in mind. That the AWS infrastructure is your last step. We provide you with the services that is going to help you deploy this application that you're...

**[05:05]** questions please do not be shy

**[05:11]** Am I that good at explaining or do you all just confuse?

**[05:15]** Put your hands up if I'm really good at explaining. Thank you. Thank you. All right. Now, last thing is how am I judging? So I'm one of the judges. OK? Please ask questions here too. So how am I judging?

**[05:30]** in my job.

**[05:32]** I work with the biggest customers in the world.

**[05:35]** Most of them know how to build apps. Probably better than in some cases we do. Your job is to tell me why. Every time you make a design choice, I want you to think about why did you pick service A, B, or C and why did you implement it this way. Think of synergies between AWS services.

**[06:00]** about AWS services, it's okay. Because you're not, I told many of you this when we came to the table, when I judge you, I do not care about technology. I don't care that you use your memcache as fast as possible and you have sub-millisecond response times from your database. If it doesn't make sense to what you're trying to solve, you will not gain points for things like that. I need you to tell me-- (static)

**[06:25]** what is the problem that you are trying to solve, work backwards from that problem, do not think about technology right now, okay? Think about a business case.

**[06:38]** a problem that you see, a pain point that a customer is feeling, and then start to create ideas around how can I begin to solve this problem. And the technology will come.

**[06:51]** When you do get to the stage of implementation, always ask yourself, what are the trade-offs? A lot of you have heard of roles called FDEs, for deployment engineers. Yeah, you might probably be one of those one day. Do you know what they're constantly evaluating in every single customer engagement? Why am I making design choice A over B for this customer?

**[07:16]** Is it a cost question? Is it a resilience question? Is it a regulatory question? Is it secure? Is this PII? These are the things you need to kind of do your best to start to ask yourself. I'm not asking you to be a solution architect, as a principal at AWS. I'm asking you to start to think of this as a mental model. This is how I want you to start to kind of design your solutions.

**[07:40]** Hopefully we're not too overwhelmed, but we're like in a little bit inspired. Is there any questions about how I'm judging?

**[07:48]** OK?

**[07:50]** If you have a question, probably somebody else has the same question. Okay, any other questions? Because I'm gonna start to now move into sharing the resources with you. So before I do that, just any last minute comments, questions or answers? (audience member speaking off mic)

**[08:12]** I'm more concerned about your implication considerations, I would say first, novelty of the problem matters to me, but it doesn't have to be completely some of the most non-novel problems that have been solved have been the most useful, right? So you just have to be the most creative thing ever, right? As long as you're solving a business problem--

**[08:37]** that you can present to the judges that is reasonable and logical and something that like we can at a basic level relate to like hey I'm trying to solve the problem x, y, or z. Oh, is that a second? That's, I'm not gonna say hey your problem's not creative or not. That's really not what is gonna happen. As long as you can show me a business case and then that your problem solves that business case and then the implementation details.

**[09:02]** that you've made those considerations and can articulate that. That's, you know, like, why did you pick service? Like, what is the synergy between using this service versus that service? Why did you-- I'll give you a fine example. I'll give you a very concrete example. It's a great question. Okay? You're going to use an AI service, right? AWS has a lot of AI services. So, if you use a service, okay--

**[09:27]** say you use a service that does

**[09:31]** recognition, facial recognition, right? And you're using a Gen A.I. service. I'm going to question you and say, "Why did you choose a Gen A.I. service? It's expensive, right? You could have used a different AWS service." So it's your job to go into Hero and Claw and say, "Hey, I want to implement this. What are my service choices?" Bob will tell you that, and more of Hero, and then you'll say, "Give it to me."

**[09:56]** my use case what fits the best right so for image recognition we have a service called recognition it's much cheaper I'm not telling you which ones you use but you see the difference is like are you gonna use bedrock or you can use recognition and why so those are the design choices right should I use serverless or non serverless if you don't know at all with these things

**[10:18]** you're gonna learn a lot. It doesn't matter if you don't know what these terms are, that is why you're sitting in this chair, right? Like 10 years ago when I was sitting in this chair, I didn't know what any of those terms meant at all. No idea. I didn't even know what the cloud was actually. So, and now I'm, I work pretty much. So that's pretty much how things go. Just be willing to learn, be okay with being a little bit, you know. (static)

**[10:40]** confused and pressured and those types of things, but just be open to learning the concepts. What can answer to a very short question, to a very great question? Does that answer your question? Yeah. I saw him on the other hand.

**[10:58]** All right.

**[10:59]** Okay, let's get started. I'm gonna share with you a link.

**[11:03]** That's going to explain how you're gonna get started. Like I said, you can start with a workshop right now.

**[11:17]** Okay, there's a website here.

**[11:20]** that I want you to go to.

**[11:25]** Can you all see that URL?

**[11:29]** Here, give me just one second.

**[11:33]** stuff

**[11:36]** This is an Amplify site and it's a one click, you'll join the workshop, okay? Below that you'll download Kira.

**[11:45]** All right.

**[11:46]** And then you have 50 credits for free if you want to use those and then you could go to the feedback forum and get like another thousand credits. So I would also recommend, you know, you have a thousand credits, so don't be shy. A thousand credits is a lot. It does get burned pretty quickly. Just to explain that concept for those of you that don't know what that means, when I say you have credits, every time you send a request to an LLM, it looks at your--

**[12:11]** [static]

**[12:21]** That's the state you want to do. Right? So you get $1,000, that's a lot. Technically you have $1,050 because you always get $50 for your credits a month. Okay?

**[12:32]** So, Lucas created this site. He'll be here in a little bit. I'm actually covering for him on this part, so I might be saying I don't know which one of you asked his questions because he sort of facilitated this. When you click on this link, you're going to use either an OTP, a builder ID, or obviously you're not an employee, unless you are, and I don't know it, but one-time password is my recommendation. If you have a builder ID, you would know it. Question?

**[12:57]** (b

**[13:00]** Yes, sorry. Let me go back to that. You're right. Let me make this huge.

**[13:13]** disrespecting.

**[13:16]** This kid.

**[13:17]** So this is the website. Can everybody see that? Is anybody not able to see it?

**[13:24]** If you guys are on a Discord, if you don't mind just sharing it around, make sure everybody gets to it.

**[13:32]** (static)

**[13:53]** on your chat services.

**[14:16]** if used.

**[14:22]** Yeah, download Hero, make sure, I would just sign up with Gmail, it's probably the email.

**[14:28]** It's what my Medicaid provider, whatever you use to, the on-key role. Just logging me one of the...

**[14:36]** and then you should get 50 credits free but we also have a cure. Do I instill the COI? Do I want to do it?

**[14:46]** Who gives you this?

**[14:55]** Does anyone still need this app? And if I did still, took a picture and put it on? I would again recommend One Time Password. You'll know if you have a builder ID like if you got an AWS cert or you did something with the task, you can use your builder ID if you want, but I recommend One Time Password. If you don't have a builder ID, just use it all the time.

**[15:18]** (heavy breathing)
